"""
Sentiment context — style instructions injected into the chat system prompt.

Fast rule-based sentiment only; does not affect model routing.
"""

from __future__ import annotations

import logging

from services.context_builder import PromptContext
from services.sentiment_analyzer import SentimentResult, analyze_sentiment

logger = logging.getLogger(__name__)

_SENTIMENT_SECTION_HEADER = "## User tone guidance"


def build_sentiment_style_instruction(sentiment: SentimentResult | str | None) -> str | None:
    """
    Map detected sentiment to a short system-prompt instruction for the assistant.

    Returns None when no special styling should be applied.
    """
    if sentiment is None:
        return None

    label = sentiment.label if isinstance(sentiment, SentimentResult) else str(sentiment)
    label = (label or "").lower().strip()

    if label in ("unknown", "neutral", "positive", "excited", ""):
        return None

    if label in ("frustrated", "negative"):
        return (
            "The user seems frustrated, negative, or annoyed. Respond with empathy, "
            "be direct and practical, and keep explanations concise—avoid overly long "
            "or preachy replies."
        )

    if label == "confused":
        return (
            "The user seems confused or uncertain. Explain clearly using simple "
            "language and a step-by-step structure."
        )

    if label == "urgent":
        return (
            "The user seems urgent. Prioritize concise, actionable steps and get "
            "to the point quickly."
        )

    return None


def resolve_sentiment_for_turn(prompt: str) -> SentimentResult | None:
    """
    Fast in-process sentiment for the current user message.

    Uses rule-based analysis only so chat streaming is not blocked.
    """
    text = (prompt or "").strip()
    if not text:
        return None
    try:
        return analyze_sentiment(text)
    except Exception as exc:
        logger.warning("Sentiment analysis skipped for chat turn: %s", exc)
        return None


def apply_sentiment_style_to_context(
    context: PromptContext,
    sentiment: SentimentResult | None,
) -> PromptContext:
    """Append tone guidance to system_prompt when a style instruction applies."""
    if sentiment is None:
        return context

    instruction = build_sentiment_style_instruction(sentiment)
    context.sentiment_label = sentiment.label
    context.sentiment_result = sentiment

    if not instruction:
        context.sentiment_style_applied = False
        return context

    block = f"{_SENTIMENT_SECTION_HEADER}\n{instruction}"
    if context.system_prompt:
        context.system_prompt = f"{context.system_prompt.strip()}\n\n{block}"
    else:
        context.system_prompt = block

    context.sentiment_style_applied = True

    system_len = len(context.system_prompt or "")
    history_chars = sum(len(m["content"]) for m in context.message_history)
    context.estimated_input_tokens = max((system_len + history_chars) // 4, 1)

    return context


def sentiment_metadata_dict(context: PromptContext) -> dict:
    """API-friendly sentiment fields from a prepared context."""
    return {
        "sentiment_label": context.sentiment_label or "",
        "sentiment_style_applied": bool(context.sentiment_style_applied),
    }
