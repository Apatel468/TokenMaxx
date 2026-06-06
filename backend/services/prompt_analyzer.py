"""
Prompt Analyzer — figures out what kind of task the user is asking for.

For the MVP we use simple keyword matching (no ML, no API calls).
Later you could swap this for a small classifier model or LiteLLM call.
"""

import re
from dataclasses import dataclass


# Task types the router understands
TASK_TYPES = [
    "coding",
    "summarization",
    "creative_writing",
    "data_analysis",
    "flashcards",
    "report",
    "general_qa",
    "translation",
]


@dataclass
class AnalysisResult:
    """Output of prompt analysis."""

    task_type: str
    confidence: float  # 0.0 to 1.0 — how sure we are about the classification
    keywords_matched: list[str]


# Keyword rules: each task type maps to words/phrases we look for
_KEYWORD_RULES: dict[str, list[str]] = {
    "coding": [
        "code", "function", "bug", "debug", "python", "javascript",
        "api", "sql", "algorithm", "implement", "refactor", "compile",
        "error", "syntax", "class", "variable", "loop", "array",
    ],
    "summarization": [
        "summarize", "summary", "tl;dr", "tldr", "brief", "condense",
        "key points", "main ideas", "short version", "in short",
    ],
    "creative_writing": [
        "write a story", "poem", "creative", "fiction", "narrative",
        "blog post", "essay", "draft", "compose", "lyrics", "script",
    ],
    "data_analysis": [
        "analyze", "analysis", "statistics", "chart", "graph", "trend",
        "dataset", "csv", "excel", "metrics", "correlation", "forecast",
    ],
    "translation": [
        "translate", "translation", "in spanish", "in french", "in german",
        "in hindi", "in chinese", "convert to", "language",
    ],
    "flashcards": [
        "flashcard", "flashcards", "study cards", "quiz cards",
    ],
    "report": [
        "report", "write a report", "business report", "annual report",
        "executive summary", "white paper", "documentation",
    ],
    "general_qa": [
        "what is", "what are", "how does", "why", "explain", "define",
        "who is", "when did", "where is", "tell me about",
    ],
}


def analyze_prompt(prompt: str) -> AnalysisResult:
    """
    Classify a user prompt into one of our task types.

    Strategy:
      1. Lowercase the prompt for case-insensitive matching.
      2. Score each task type by counting keyword hits.
      3. Pick the highest-scoring type; fall back to general_qa.
    """
    normalized = prompt.lower().strip()
    scores: dict[str, list[str]] = {task: [] for task in TASK_TYPES}

    for task_type, keywords in _KEYWORD_RULES.items():
        for keyword in keywords:
            # Use word boundaries so "class" doesn't match inside "classroom"
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, normalized):
                scores[task_type].append(keyword)

    # Find the task type with the most keyword matches
    best_task = "general_qa"
    best_matches: list[str] = []
    best_score = 0

    for task_type, matches in scores.items():
        if len(matches) > best_score:
            best_score = len(matches)
            best_task = task_type
            best_matches = matches

    # Rough confidence: more keyword hits = more confident
    if best_score == 0:
        confidence = 0.5  # no keywords matched — default guess
    else:
        confidence = min(0.5 + best_score * 0.15, 0.95)

    return AnalysisResult(
        task_type=best_task,
        confidence=confidence,
        keywords_matched=best_matches,
    )
