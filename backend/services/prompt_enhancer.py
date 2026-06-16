"""
Prompt Enhancer — AI Prompt Engineering Agent (Phase 4+).

Primary: LiteLLM + Groq (llama-3.1-8b-instant) rewrites the user prompt for clarity.
Fallback: Rule-based templates if Groq is unavailable or returns invalid JSON.

Runs after classification and before routing/model calls.
"""

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

# ---------------------------------------------------------------------------
# Rule-based fallback (used when AI enhancement fails)
# ---------------------------------------------------------------------------

_SAFETY_RULES = (
    "Do not change the user's meaning or intent.",
    "Do not add facts, data, or claims that the user did not provide.",
    "If information is missing, say so instead of guessing.",
)

_TASK_RULES: dict[str, dict[str, str]] = {
    "flashcards": {
        "system": (
            "You create educational flashcards. Use a clear question/answer (Q/A) format. "
            "One concept per card. Keep answers accurate and concise."
        ),
        "user_suffix": (
            "Format your response as clear Q/A flashcards. "
            "Use one question and one answer per card."
        ),
        "reason": "Added flashcard Q/A formatting instructions (rule fallback).",
    },
    "coding": {
        "system": (
            "You help with programming tasks. Provide clean, readable code with helpful "
            "comments. Mention edge cases and assumptions when relevant."
        ),
        "user_suffix": (
            "Provide clean code with brief comments. "
            "Call out edge cases or assumptions where helpful."
        ),
        "reason": "Added coding quality and edge-case guidance (rule fallback).",
    },
    "report": {
        "system": (
            "You write professional reports. Use clear headings, logical structure, "
            "and concise language suitable for a business audience."
        ),
        "user_suffix": (
            "Structure the response as a professional report with headings "
            "and concise language."
        ),
        "reason": "Added professional report structure guidance (rule fallback).",
    },
    "summarization": {
        "system": (
            "You summarize content clearly. Use bullet points and highlight "
            "the most important takeaways."
        ),
        "user_suffix": (
            "Provide a bullet-point summary with key takeaways at the end."
        ),
        "reason": "Added bullet summary and key takeaways guidance (rule fallback).",
    },
    "general_qa": {
        "system": (
            "You answer questions clearly and concisely. "
            "Stay focused on what the user asked."
        ),
        "user_suffix": "Provide a clear, concise answer focused on the question.",
        "reason": "Added clear and concise answer guidance (rule fallback).",
    },
}

_TASK_ALIASES: dict[str, str] = {
    "creative_writing": "creative",
    "data_analysis": "research",
    "translation": "general_qa",
    "writing": "writing",
    "summarization": "summarization",
    "math": "math",
    "research": "research",
    "reasoning": "reasoning",
    "creative": "creative",
    "classification": "classification",
    "report": "report",
}

# Task hints sent to the AI prompt engineer
_AI_TASK_HINTS: dict[str, str] = {
    "flashcards": "Ask for clear Q/A flashcard format, one concept per card.",
    "coding": "Ask for clean code, helpful comments, and mention of edge cases.",
    "report": "Ask for professional structure with headings and concise language.",
    "summarization": "Ask for bullet summary and key takeaways.",
    "general_qa": "Ask for a clear, concise, focused answer.",
}


@dataclass
class EnhancementResult:
    """Output of the prompt enhancement step."""

    enhanced_prompt: str
    system_prompt: str
    enhancement_reason: str
    enhancement_method: str  # "ai" or "rule_fallback"


def _has_groq_key() -> bool:
    """Return True if GROQ_API_KEY exists — we never read or log its value."""
    return bool(os.getenv(GROQ_ENV_KEY, "").strip())


def _to_litellm_model(groq_model: str) -> str:
    """Convert YAML-style model name to LiteLLM format."""
    if groq_model.startswith("groq/"):
        return groq_model
    return f"groq/{groq_model}"


def _resolve_task_key(task_type: str) -> str:
    """Pick the rule/hint set for this task type."""
    if task_type in _TASK_RULES:
        return task_type
    return _TASK_ALIASES.get(task_type, "general_qa")


def _format_conversation_context(conversation_history: list[dict]) -> str:
    """Turn prior messages into readable text for the AI agent."""
    if not conversation_history:
        return ""

    lines: list[str] = []
    for msg in conversation_history:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines)


def _extract_json_object(text: str) -> dict:
    """Parse JSON from the enhancer response (handles markdown fences)."""
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return json.loads(cleaned)


_PRESERVE_INTENT_SUFFIX_RE = re.compile(
    r"\n\n\[Original user request — preserve this intent: [\s\S]*?\]\s*$",
    re.IGNORECASE,
)


def format_enhanced_prompt_for_display(enhanced_prompt: str) -> str:
    """
    Return enhanced prompt text suitable for the UI viewer.

    Strips internal safety suffixes appended for the downstream model — the
    original prompt is shown separately in the viewer.
    """
    text = (enhanced_prompt or "").strip()
    if not text:
        return ""
    return _PRESERVE_INTENT_SUFFIX_RE.sub("", text).strip()


def _build_ai_agent_messages(
    original_prompt: str,
    task_type: str,
    difficulty: str,
    risk_level: str,
    conversation_history: list[dict],
) -> list[dict]:
    """
    Build messages for the Prompt Engineering Agent (Groq via LiteLLM).

    The agent returns JSON with enhanced_prompt, system_prompt, enhancement_reason.
    """
    task_key = _resolve_task_key(task_type)
    task_hint = _AI_TASK_HINTS.get(task_key, _AI_TASK_HINTS["general_qa"])
    context_block = _format_conversation_context(conversation_history)

    system_prompt = f"""You are a Prompt Engineering Agent for an LLM routing system.

Your job: improve how a user's request is written BEFORE it is sent to a task-specific AI model.

Respond with JSON ONLY — no markdown, no extra text.

Required JSON schema:
{{
  "enhanced_prompt": "<rewritten user request — clearer structure and task instructions>",
  "system_prompt": "<system message for the downstream AI that will answer the user>",
  "enhancement_reason": "<one short sentence explaining what you improved>"
}}

Rules you MUST follow:
- Preserve the user's original meaning and intent exactly.
- Do NOT add facts, data, names, or claims the user did not provide.
- Improve clarity, structure, formatting instructions, and task guidance.
- Task type: {task_type}. Difficulty: {difficulty}. Risk level: {risk_level}.
- Task guidance: {task_hint}
- enhanced_prompt should be what the downstream model reads as the user message.
- system_prompt should tell the downstream model how to behave (tone, format, safety).
- If conversation context is provided, use it — do not invent details beyond it.
"""

    user_parts = [f"Original user request:\n{original_prompt.strip()}"]
    if context_block:
        user_parts.insert(
            0,
            "Conversation context (use for reference only — do not invent beyond this):\n"
            f"{context_block}\n",
        )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


def _validate_ai_output(parsed: dict, original_prompt: str) -> EnhancementResult:
    """
    Validate AI JSON output and fill safe defaults for missing fields.

    Raises ValueError if required fields are empty after validation.
    """
    enhanced = str(parsed.get("enhanced_prompt", "")).strip()
    system = str(parsed.get("system_prompt", "")).strip()
    reason = str(parsed.get("enhancement_reason", "")).strip()

    if not enhanced:
        raise ValueError("AI enhancer returned empty enhanced_prompt")

    if not system:
        system = (
            "Answer the user clearly and accurately. "
            "Do not add facts the user did not provide."
        )

    if not reason:
        reason = "AI prompt engineer improved clarity and task instructions."

    return EnhancementResult(
        enhanced_prompt=enhanced,
        system_prompt=system,
        enhancement_reason=reason,
        enhancement_method="ai",
    )


def _enhance_with_ai(
    original_prompt: str,
    task_type: str,
    difficulty: str,
    risk_level: str,
    conversation_history: list[dict],
) -> EnhancementResult:
    """
    Call Groq via LiteLLM to rewrite/enhance the prompt.

    Raises on API errors or invalid JSON so enhance_prompt can fall back.
    """
    import litellm

    litellm_model = _to_litellm_model(get_auxiliary_model("enhancer"))
    messages = _build_ai_agent_messages(
        original_prompt,
        task_type,
        difficulty,
        risk_level,
        conversation_history,
    )

    logger.info(
        "AI prompt engineer | model=%s | task=%s",
        litellm_model,
        task_type,
    )

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
        raise ValueError("AI prompt engineer returned empty response")

    parsed = _extract_json_object(text)
    result = _validate_ai_output(parsed, original_prompt)

    logger.info(
        "AI prompt engineer success | method=%s | reason=%s",
        result.enhancement_method,
        result.enhancement_reason[:80],
    )
    return result


def _enhance_with_rules(
    original_prompt: str,
    task_type: str,
    difficulty: str,
    risk_level: str,
    conversation_history: list[dict],
) -> EnhancementResult:
    """
    Rule-based prompt wrapping — fallback when Groq is unavailable or fails.

    Uses fixed templates per task type (no API call).
    """
    prompt = original_prompt.strip()
    task_key = _resolve_task_key(task_type)
    rules = _TASK_RULES[task_key]
    safety_block = " ".join(_SAFETY_RULES)

    system_prompt = (
        f"{rules['system']}\n\n"
        f"Task difficulty: {difficulty}. Risk level: {risk_level}.\n"
        f"{safety_block}"
    )

    parts: list[str] = []
    context_block = _format_conversation_context(conversation_history)
    if context_block:
        parts.append(
            "Use the conversation below for context. "
            "Do not invent details beyond what appears here.\n\n"
            "--- Conversation so far ---\n"
            f"{context_block}\n"
            "--- End of conversation ---"
        )

    parts.append(f"User request (preserve this intent exactly):\n{prompt}")
    parts.append(rules["user_suffix"])

    enhanced_prompt = "\n\n".join(parts)

    reason_parts = [rules["reason"]]
    if context_block:
        reason_parts.append(f"Included {len(conversation_history)} prior message(s).")

    return EnhancementResult(
        enhanced_prompt=enhanced_prompt,
        system_prompt=system_prompt,
        enhancement_reason=" ".join(reason_parts),
        enhancement_method="rule_fallback",
    )


def enhance_prompt(
    original_prompt: str,
    task_type: str,
    difficulty: str,
    risk_level: str,
    conversation_history: list[dict] | None = None,
) -> EnhancementResult:
    """
    Enhance a user prompt before routing and model generation.

    1. If GROQ_API_KEY is set → AI Prompt Engineering Agent (Groq + LiteLLM)
    2. On failure or missing key → rule-based fallback

    Args:
        original_prompt: Exactly what the user typed.
        task_type: From prompt_analyzer.
        difficulty: easy | medium | hard.
        risk_level: low | medium | high.
        conversation_history: Prior turns without the new message.

    Returns:
        EnhancementResult including enhancement_method ("ai" or "rule_fallback").
    """
    history = conversation_history or []

    if not original_prompt or not original_prompt.strip():
        fallback = _enhance_with_rules(
            original_prompt or "",
            task_type,
            difficulty,
            risk_level,
            history,
        )
        fallback.enhancement_reason = "Empty prompt — used rule fallback."
        return fallback

    if _has_groq_key():
        try:
            return _enhance_with_ai(
                original_prompt,
                task_type,
                difficulty,
                risk_level,
                history,
            )
        except Exception as exc:
            logger.warning(
                "AI prompt engineer failed (%s) — using rule fallback",
                exc,
            )
    else:
        logger.info(
            "%s not set — using rule-based prompt enhancement",
            GROQ_ENV_KEY,
        )

    return _enhance_with_rules(
        original_prompt,
        task_type,
        difficulty,
        risk_level,
        history,
    )
