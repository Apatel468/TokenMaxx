"""
Prompt Analyzer — figures out what kind of task the user is asking for.

Primary method (when GROQ_API_KEY is set):
  - Send the prompt to a fast Groq model via LiteLLM
  - Model returns JSON with task_type, difficulty, risk_level, reason
  - task_type must be one of the keys in config/models.yaml

Fallback (no API key or Groq error):
  - Original keyword matching — no extra API call
"""

import json
import logging
import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv

from services.config_loader import (
    get_allowed_task_types,
    get_classifier_config,
    get_default_task_type,
)

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_ENV_KEY = "GROQ_API_KEY"

# Allowed values for LLM classifier output (not stored in YAML)
_DIFFICULTY_VALUES = ("easy", "medium", "hard")
_RISK_LEVEL_VALUES = ("low", "medium", "high")


@dataclass
class AnalysisResult:
    """Output of prompt analysis."""

    task_type: str
    confidence: float  # 0.0 to 1.0
    keywords_matched: list[str]
    difficulty: str = "medium"
    risk_level: str = "low"
    reason: str = ""
    used_llm: bool = False  # True when Groq classifier succeeded


# Keyword fallback still recognizes these; config_loader maps aliases to YAML keys
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


def _has_groq_key() -> bool:
    """Return True if GROQ_API_KEY exists — we never read or log its value."""
    return bool(os.getenv(GROQ_ENV_KEY, "").strip())


def _to_litellm_model(groq_model: str) -> str:
    """Convert YAML model name to LiteLLM format (e.g. groq/llama-3.1-8b-instant)."""
    if groq_model.startswith("groq/"):
        return groq_model
    return f"groq/{groq_model}"


def _build_classifier_messages(prompt: str, allowed_types: list[str]) -> list[dict]:
    """
    Build the system + user messages sent to the Groq classifier.

    The system prompt lists allowed task types from models.yaml and asks
    for JSON-only output with a fixed schema.
    """
    types_list = ", ".join(allowed_types)
    default_task = get_default_task_type()

    system_prompt = f"""You are a prompt classifier for an LLM routing system.

Read the user's prompt and respond with JSON ONLY — no markdown, no extra text.

Required JSON schema:
{{
  "task_type": "<one of: {types_list}>",
  "difficulty": "<easy | medium | hard>",
  "risk_level": "<low | medium | high>",
  "reason": "<one short sentence explaining your choice>"
}}

Rules:
- task_type MUST be exactly one of: {types_list}
- If unsure, use "{default_task}"
- difficulty: how complex the task is for an AI to complete well
- risk_level: low = safe factual Q&A; medium = advice/drafts; high = medical/legal/financial/safety-critical
- reason: brief explanation (max 20 words)
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt.strip()},
    ]


def _extract_json_object(text: str) -> dict:
    """
    Parse JSON from the classifier response.

    Handles plain JSON or JSON wrapped in ``` fences if the model adds them.
    """
    cleaned = text.strip()

    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    return json.loads(cleaned)


def _validate_classifier_output(parsed: dict, allowed_types: list[str]) -> AnalysisResult:
    """
    Ensure the LLM JSON matches our schema and allowed task types.

    Invalid fields are replaced with safe defaults instead of failing.
    """
    default_task = get_default_task_type()

    task_type = str(parsed.get("task_type", default_task)).strip().lower()
    if task_type not in allowed_types:
        logger.warning(
            "Classifier returned unknown task_type=%r — using %s",
            task_type,
            default_task,
        )
        task_type = default_task

    difficulty = str(parsed.get("difficulty", "medium")).strip().lower()
    if difficulty not in _DIFFICULTY_VALUES:
        difficulty = "medium"

    risk_level = str(parsed.get("risk_level", "low")).strip().lower()
    if risk_level not in _RISK_LEVEL_VALUES:
        risk_level = "low"

    reason = str(parsed.get("reason", "")).strip()
    if not reason:
        reason = f"Classified as {task_type} by Groq classifier."

    return AnalysisResult(
        task_type=task_type,
        confidence=0.85,
        keywords_matched=[],
        difficulty=difficulty,
        risk_level=risk_level,
        reason=reason,
        used_llm=True,
    )


def _analyze_with_llm(prompt: str) -> AnalysisResult:
    """
    Classify a prompt using LiteLLM + Groq.

    Raises on API errors or unparseable JSON so analyze_prompt can fall back.
    """
    import litellm

    allowed_types = get_allowed_task_types()
    classifier = get_classifier_config()
    groq_model = classifier["model"]
    litellm_model = _to_litellm_model(groq_model)
    messages = _build_classifier_messages(prompt, allowed_types)

    logger.info("LLM classifier | model=%s | allowed_types=%s", litellm_model, allowed_types)

    # Try JSON mode first (supported on many Groq models via LiteLLM)
    try:
        response = litellm.completion(
            model=litellm_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
    except Exception:
        # Some models reject response_format — retry without it
        response = litellm.completion(
            model=litellm_model,
            messages=messages,
            temperature=0,
        )

    text = response.choices[0].message.content or ""
    if not text.strip():
        raise ValueError("Classifier returned empty response")

    parsed = _extract_json_object(text)
    result = _validate_classifier_output(parsed, allowed_types)

    logger.info(
        "LLM classifier success | task_type=%s | difficulty=%s | risk=%s",
        result.task_type,
        result.difficulty,
        result.risk_level,
    )
    return result


def _analyze_with_keywords(prompt: str) -> AnalysisResult:
    """
    Original keyword-based classifier — used when Groq is unavailable.

    Returns extra task types (e.g. summarization) that config_loader
    maps to YAML keys via aliases.
    """
    normalized = prompt.lower().strip()
    scores: dict[str, list[str]] = {task: [] for task in TASK_TYPES}

    for task_type, keywords in _KEYWORD_RULES.items():
        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, normalized):
                scores[task_type].append(keyword)

    best_task = get_default_task_type()
    best_matches: list[str] = []
    best_score = 0

    for task_type, matches in scores.items():
        if len(matches) > best_score:
            best_score = len(matches)
            best_task = task_type
            best_matches = matches

    if best_score == 0:
        confidence = 0.5
        reason = f"No keywords matched — defaulting to {best_task}."
    else:
        confidence = min(0.5 + best_score * 0.15, 0.95)
        reason = f"Keyword match ({', '.join(best_matches[:3])})."

    return AnalysisResult(
        task_type=best_task,
        confidence=confidence,
        keywords_matched=best_matches,
        difficulty="medium",
        risk_level="low",
        reason=reason,
        used_llm=False,
    )


def analyze_prompt(prompt: str) -> AnalysisResult:
    """
    Classify a user prompt into a task type for model routing.

    1. If GROQ_API_KEY is set → Groq LLM classifier (JSON output)
    2. On any failure → keyword classifier fallback
    3. Router uses task_type → config/models.yaml lookup
    """
    if not prompt or not prompt.strip():
        default_task = get_default_task_type()
        return AnalysisResult(
            task_type=default_task,
            confidence=0.5,
            keywords_matched=[],
            reason="Empty prompt — using default task type.",
            used_llm=False,
        )

    if _has_groq_key():
        try:
            return _analyze_with_llm(prompt)
        except Exception as exc:
            logger.warning(
                "LLM classifier failed (%s) — falling back to keywords",
                exc,
            )
    else:
        logger.info("%s not set — using keyword classifier", GROQ_ENV_KEY)

    return _analyze_with_keywords(prompt)
