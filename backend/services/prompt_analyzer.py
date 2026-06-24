"""
Prompt Analyzer — classifies user prompts before routing.

Primary: LLM classifier (Groq llama-3.1-8b-instant) when GROQ_API_KEY is set.
Fallback: keyword rules (no API call).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from services.llm_classifier import classify_prompt_with_llm

logger = logging.getLogger(__name__)

# Task types returned by analyze_prompt (LLM + rule fallback).
TASK_TYPES = [
    "general_qa",
    "coding",
    "reasoning",
    "writing",
    "summarization",
    "math",
    "research",
    "creative",
    "report",
    "business",
    "classification",
    "web_research",
]


@dataclass
class AnalysisResult:
    """Output of prompt analysis."""

    task_type: str
    confidence: float
    keywords_matched: list[str]
    difficulty: str = "medium"
    risk_level: str = "low"
    classification_reason: str = ""
    classification_method: str = "rule_fallback"  # "llm" | "rule_fallback"


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
    "creative": [
        "write a story", "poem", "creative", "fiction", "narrative",
        "blog post", "essay", "draft", "compose", "lyrics", "script",
    ],
    "writing": [
        "rewrite", "edit", "paragraph", "email", "letter",
        "tone", "wording", "proofread",
    ],
    "research": [
        "research", "analyze", "analysis", "statistics", "chart", "graph",
        "trend", "dataset", "csv", "metrics", "correlation", "study",
    ],
    "math": [
        "calculate", "equation", "algebra", "calculus", "integral",
        "derivative", "probability", "geometry", "math", "solve for",
    ],
    "reasoning": [
        "logic", "deduce", "infer", "step by step", "prove", "why does",
        "compare and contrast", "evaluate", "trade-off",
    ],
    "report": [
        "report", "briefing", "memo", "white paper", "executive summary",
        "findings", "recommendations", "rfp", "proposal", "board presentation",
    ],
    "business": [
        "business strategy", "fortune 500", "executive strategy", "market strategy",
        "go-to-market", "go to market", "competitive analysis", "enterprise",
        "implementation roadmap", "compliance", "procurement", "strategic plan",
        "stakeholders", "risk analysis", "financial impact", "strategy",
    ],
    "classification": [
        "classify", "categorize", "label", "tag", "sort into",
        "which category", "type of",
    ],
    "web_research": [
        "latest", "current", "recent news", "pricing", "price", "cost per",
        "today", "announcement", "competitor", "market research",
        "company research", "enterprise plan", "release notes",
        "what is the current", "as of today", "right now", "compare",
        "versus", "documentation", "docs", "look up online",
    ],
    "general_qa": [
        "what is", "what are", "how does", "why", "explain", "define",
        "who is", "when did", "where is", "tell me about",
    ],
}


def _analyze_with_rules(prompt: str) -> AnalysisResult:
    """Keyword-based classifier used when the LLM path is unavailable."""
    normalized = prompt.lower().strip()
    scores: dict[str, list[str]] = {task: [] for task in TASK_TYPES}

    for task_type, keywords in _KEYWORD_RULES.items():
        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, normalized):
                scores[task_type].append(keyword)

    best_task = "general_qa"
    best_matches: list[str] = []
    best_score = 0

    for task_type, matches in scores.items():
        if len(matches) > best_score:
            best_score = len(matches)
            best_task = task_type
            best_matches = matches

    if best_score == 0:
        confidence = 0.5
        reason = "No strong keyword match — defaulted to general Q&A."
    else:
        confidence = min(0.5 + best_score * 0.15, 0.95)
        reason = f"Keyword match suggests {best_task.replace('_', ' ')}."

    return AnalysisResult(
        task_type=best_task,
        confidence=confidence,
        keywords_matched=best_matches,
        classification_reason=reason,
        classification_method="rule_fallback",
    )


def analyze_prompt(prompt: str) -> AnalysisResult:
    """
    Classify a user prompt into a routing task type.

    1. Try LLM classifier (Groq) when API key is available.
    2. On any failure, use keyword rules.
    """
    try:
        llm_result = classify_prompt_with_llm(prompt)
        return AnalysisResult(
            task_type=llm_result.task_type,
            confidence=llm_result.confidence,
            keywords_matched=[],
            classification_reason=llm_result.reason,
            classification_method="llm",
        )
    except Exception as exc:
        logger.warning("LLM classifier failed (%s) — using rule fallback", exc)

    return _analyze_with_rules(prompt)
