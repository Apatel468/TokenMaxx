"""
Sentiment Analyzer — classifies user message tone before or alongside chat.

Primary: fast keyword + pattern rules (no API latency).
Designed for extension: emotion scores, toxicity, mood tracking can plug in later.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

ANALYZER_VERSION = "v1"

SENTIMENT_LABELS = (
    "positive",
    "neutral",
    "negative",
    "excited",
    "frustrated",
    "confused",
    "urgent",
)

# Priority when multiple signals match (higher wins).
_LABEL_PRIORITY = {
    "urgent": 7,
    "frustrated": 6,
    "confused": 5,
    "excited": 4,
    "negative": 3,
    "positive": 2,
    "neutral": 1,
}

_KEYWORD_RULES: dict[str, list[str]] = {
    "urgent": [
        "urgent", "asap", "immediately", "right now", "deadline", "hurry",
        "time sensitive", "critical", "emergency", "need this today",
        "by end of day", "eod", "as soon as possible",
    ],
    "frustrated": [
        "frustrated", "annoyed", "still not working", "doesn't work",
        "does not work", "not working", "again", "ugh", "why won't",
        "fed up", "sick of", "this is ridiculous", "broken", "useless",
        "waste of time", "keeps failing",
    ],
    "confused": [
        "confused", "don't understand", "do not understand", "unclear",
        "what do you mean", "not sure", "help me understand", "lost",
        "doesn't make sense", "does not make sense", "i'm stuck",
        "can you clarify", "clarify", "what does this mean",
    ],
    "excited": [
        "excited", "can't wait", "cannot wait", "wow", "amazing",
        "awesome", "fantastic", "love this", "so cool", "brilliant",
        "incredible", "yay", "let's go", "lets go",
    ],
    "negative": [
        "hate", "awful", "terrible", "bad", "disappointed", "angry",
        "worst", "horrible", "unhappy", "upset", "sad", "regret",
        "unacceptable", "poor quality", "not good",
    ],
    "positive": [
        "thanks", "thank you", "great", "love", "wonderful", "happy",
        "appreciate", "helpful", "perfect", "excellent", "good job",
        "well done", "nice", "pleased", "grateful",
    ],
}


@dataclass
class SentimentResult:
    """Output of sentiment analysis."""

    label: str
    confidence: float  # 0.0–1.0 internally; API exposes 0–100
    explanation: str
    method: str = "rules"
    signals: list[str] = field(default_factory=list)
    analyzer_version: str = ANALYZER_VERSION
    # Reserved for future emotion / toxicity payloads
    metadata: dict = field(default_factory=dict)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _score_label(normalized: str, label: str, keywords: list[str]) -> tuple[float, list[str]]:
    matches: list[str] = []
    for keyword in keywords:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, normalized):
            matches.append(keyword)

    if not matches:
        return 0.0, []

    score = min(0.55 + len(matches) * 0.12, 0.95)
    return score, matches


def _boost_excited(normalized: str, base_score: float) -> float:
    exclamations = normalized.count("!")
    if exclamations >= 2:
        return min(base_score + 0.1, 0.92)
    if exclamations == 1 and any(
        w in normalized for w in ("wow", "amazing", "awesome", "great", "excited")
    ):
        return min(base_score + 0.08, 0.9)
    return base_score


def _analyze_with_rules(text: str) -> SentimentResult:
    normalized = _normalize(text)
    if not normalized:
        return SentimentResult(
            label="neutral",
            confidence=0.5,
            explanation="Empty message — treated as neutral.",
            method="rules",
        )

    scores: dict[str, tuple[float, list[str]]] = {}
    for label, keywords in _KEYWORD_RULES.items():
        score, matches = _score_label(normalized, label, keywords)
        if score > 0:
            if label == "excited":
                score = _boost_excited(normalized, score)
            scores[label] = (score, matches)

    if not scores:
        return SentimentResult(
            label="neutral",
            confidence=0.55,
            explanation="No strong emotional signals detected — neutral tone.",
            method="rules",
        )

    best_label = max(
        scores.keys(),
        key=lambda lbl: (scores[lbl][0], _LABEL_PRIORITY.get(lbl, 0)),
    )
    best_score, best_matches = scores[best_label]
    readable = best_label.replace("_", " ")
    if len(best_matches) == 1:
        reason = f'Matched cue "{best_matches[0]}" — reads as {readable}.'
    else:
        reason = f'Matched {len(best_matches)} cues — reads as {readable}.'

    return SentimentResult(
        label=best_label,
        confidence=round(best_score, 3),
        explanation=reason,
        method="rules",
        signals=best_matches,
    )


def analyze_sentiment(text: str) -> SentimentResult:
    """
    Classify user message sentiment.

    Runs synchronously; callers should use asyncio.to_thread for non-blocking HTTP.
    """
    if not text or not str(text).strip():
        return SentimentResult(
            label="neutral",
            confidence=0.5,
            explanation="Empty message — treated as neutral.",
            method="rules",
        )

    try:
        return _analyze_with_rules(str(text))
    except Exception as exc:
        logger.warning("Sentiment analysis failed: %s", exc)
        raise


def unknown_sentiment_result() -> SentimentResult:
    """Fallback when analysis cannot run."""
    return SentimentResult(
        label="unknown",
        confidence=0.0,
        explanation="Unable to determine sentiment",
        method="error",
    )
