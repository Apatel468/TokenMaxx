"""
LLM Prompt Classifier — task-type detection via a cheap Groq model.

Uses llama-3.1-8b-instant (config: auxiliary.classifier) before routing.
Returns structured JSON; callers fall back to rule-based analysis on failure.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv

from services.config_loader import get_auxiliary_model

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_ENV_KEY = "GROQ_API_KEY"

# Task types the LLM may return (must match routing task_profiles / aliases).
SUPPORTED_TASK_TYPES: frozenset[str] = frozenset(
    {
        "general_qa",
        "coding",
        "reasoning",
        "writing",
        "summarization",
        "math",
        "research",
        "creative",
        "report",
        "classification",
    }
)


@dataclass
class LLMClassificationResult:
    """Structured output from the LLM classifier."""

    task_type: str
    confidence: float
    reason: str


def _has_groq_key() -> bool:
    return bool(os.getenv(GROQ_ENV_KEY, "").strip())


def _to_litellm_model(groq_model: str) -> str:
    if groq_model.startswith("groq/"):
        return groq_model
    return f"groq/{groq_model}"


def _extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return json.loads(cleaned)


def _validate_llm_output(parsed: dict) -> LLMClassificationResult:
    task_type = str(parsed.get("task_type", "")).strip().lower()
    if task_type not in SUPPORTED_TASK_TYPES:
        raise ValueError(f"LLM classifier returned invalid task_type: {task_type!r}")

    try:
        confidence = float(parsed.get("confidence", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("LLM classifier returned invalid confidence") from exc
    confidence = max(0.0, min(1.0, confidence))

    reason = str(parsed.get("reason", "")).strip()
    # Keep a short user-facing reason — no chain-of-thought.
    reason = reason[:200]
    if not reason:
        reason = f"Prompt classified as {task_type.replace('_', ' ')}."

    return LLMClassificationResult(
        task_type=task_type,
        confidence=confidence,
        reason=reason,
    )


def classify_prompt_with_llm(prompt: str) -> LLMClassificationResult:
    """
    Classify a user prompt with Groq + llama-3.1-8b-instant.

    Raises on missing API key, API errors, or invalid JSON output.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Cannot classify an empty prompt.")

    if not _has_groq_key():
        raise RuntimeError(f"{GROQ_ENV_KEY} is not set")

    import litellm

    model_id = get_auxiliary_model("classifier")
    litellm_model = _to_litellm_model(model_id)
    task_list = ", ".join(sorted(SUPPORTED_TASK_TYPES))

    system_prompt = f"""You are a prompt classifier for an LLM routing system.

Classify the user's message into exactly ONE task type from this list:
{task_list}

Respond with JSON ONLY — no markdown, no extra text.

Required JSON schema:
{{
  "task_type": "<one of the task types above>",
  "confidence": <number between 0 and 1>,
  "reason": "<one short sentence explaining the classification — no chain-of-thought>"
}}

Rules:
- Pick the single best-matching task type.
- confidence reflects how sure you are (0.0 to 1.0).
- reason must be one brief sentence for the user interface.
- Do not include reasoning steps or internal deliberation in reason.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt.strip()},
    ]

    logger.info("LLM classifier | model=%s", litellm_model)

    try:
        response = litellm.completion(
            model=litellm_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
    except Exception:
        response = litellm.completion(
            model=litellm_model,
            messages=messages,
            temperature=0,
        )

    text = response.choices[0].message.content or ""
    if not text.strip():
        raise ValueError("LLM classifier returned empty response")

    parsed = _extract_json_object(text)
    result = _validate_llm_output(parsed)

    logger.info(
        "LLM classifier success | task=%s | confidence=%.2f",
        result.task_type,
        result.confidence,
    )
    return result
