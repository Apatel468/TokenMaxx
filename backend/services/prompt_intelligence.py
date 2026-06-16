"""
Prompt Intelligence Engine v2 — analyze then enhance by task, complexity, and persona.

Runs after classification and before routing. Produces a structured PromptAnalysis
with a clean enhanced_prompt (no internal scaffolding shown to users).
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

SUPPORTED_TASK_TYPES: frozenset[str] = frozenset(
    {
        "general_qa",
        "coding",
        "reasoning",
        "writing",
        "summarization",
        "research",
        "business",
        "education",
        "creative",
        "data_analysis",
    }
)

_TASK_ALIASES: dict[str, str] = {
    "report": "business",
    "math": "reasoning",
    "classification": "general_qa",
    "creative_writing": "creative",
    "flashcards": "education",
    "translation": "writing",
}

_PERSONAS: dict[str, str] = {
    "coding": "Senior Software Engineer",
    "business": "Business Consultant",
    "research": "Research Analyst",
    "writing": "Professional Editor",
    "education": "Teacher/Tutor",
    "data_analysis": "Data Analyst",
    "general_qa": "Helpful Expert",
    "reasoning": "Critical Reasoning Expert",
    "summarization": "Professional Editor",
    "creative": "Creative Writer",
}

_OUTPUT_FORMATS: dict[str, str] = {
    "general_qa": "Clear, direct answer with key points first",
    "coding": "Clean code with comments plus a brief explanation",
    "reasoning": "Step-by-step logical explanation with a clear conclusion",
    "writing": "Polished prose with appropriate structure and tone",
    "summarization": "Concise bullet summary with key takeaways",
    "research": "Structured analysis with evidence and implications",
    "business": "Executive summary, findings, and actionable recommendations",
    "education": "Clear explanation with examples and a short recap",
    "creative": "Creative draft matching the requested style and length",
    "data_analysis": "Insights, metrics, and data-driven recommendations",
}

_COMPLEX_KEYWORDS = (
    "step by step",
    "analyze",
    "analysis",
    "architecture",
    "assumptions",
    "compare",
    "constraints",
    "debug",
    "design",
    "evaluate",
    "implement",
    "optimize",
    "prove",
    "refactor",
    "requirements",
    "trade-off",
)

_INTERNAL_NOTE_PATTERNS = (
    re.compile(
        r"\n\n\[Original user request — preserve this intent:[\s\S]*?\]\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^User request \(preserve this intent exactly\):\s*",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"Use the conversation below for context\.[\s\S]*?--- End of conversation ---\s*",
        re.IGNORECASE,
    ),
)


@dataclass
class PromptAnalysis:
    """Structured output of the Prompt Intelligence Engine v2."""

    original_prompt: str
    task_type: str
    complexity_score: int
    complexity_level: str
    persona: str
    output_format: str
    enhancement_strategy: str
    enhanced_prompt: str
    system_prompt: str = ""
    enhancement_reason: str = ""
    enhancement_method: str = "rule_fallback"


def normalize_task_type(task_type: str) -> str:
    """Map router/classifier task types to v2 enhancement task types."""
    key = (task_type or "general_qa").strip().lower()
    if key in SUPPORTED_TASK_TYPES:
        return key
    return _TASK_ALIASES.get(key, "general_qa")


def compute_complexity_score(
    prompt: str,
    task_type: str,
    *,
    difficulty: str = "medium",
) -> int:
    """Estimate prompt complexity on a 0–100 scale."""
    text = (prompt or "").strip().lower()
    token_est = max(len(text) // 4, 1)

    length_score = min(token_est / 10.0, 35.0)
    task_score = 12.0 if task_type in {
        "reasoning",
        "research",
        "business",
        "coding",
        "data_analysis",
    } else 0.0
    difficulty_score = {"easy": 0.0, "medium": 10.0, "hard": 22.0}.get(
        difficulty, 10.0
    )
    keyword_score = 15.0 if any(keyword in text for keyword in _COMPLEX_KEYWORDS) else 0.0
    structure_score = 10.0 if len(text) > 400 else 0.0

    score = int(
        min(length_score + task_score + difficulty_score + keyword_score + structure_score, 100)
    )

    if task_type == "coding" and any(
        token in text
        for token in ("function", "implement", "code", "debug", "class", "api")
    ):
        score = max(score, 40)
    if task_type in {"business", "writing", "research", "data_analysis"} and len(text) > 50:
        score = max(score, 42)
    if task_type == "reasoning" and any(keyword in text for keyword in _COMPLEX_KEYWORDS):
        score = max(score, 68)
    if any(keyword in text for keyword in _COMPLEX_KEYWORDS):
        score = max(score, 68)

    return min(score, 100)


def complexity_level_from_score(score: int) -> str:
    """Map a 0–100 score to simple, medium, or complex."""
    if score <= 33:
        return "simple"
    if score <= 66:
        return "medium"
    return "complex"


def select_persona(task_type: str) -> str:
    return _PERSONAS.get(task_type, _PERSONAS["general_qa"])


def select_output_format(task_type: str) -> str:
    return _OUTPUT_FORMATS.get(task_type, _OUTPUT_FORMATS["general_qa"])


def select_enhancement_strategy(task_type: str, complexity_level: str) -> str:
    if complexity_level == "simple":
        return "minimal_clarity"
    if complexity_level == "medium":
        return "structured_clarity"
    return f"full_specification_{task_type}"


def sanitize_enhanced_prompt(text: str) -> str:
    """Remove internal scaffolding that should never appear in the UI."""
    cleaned = (text or "").strip()
    for pattern in _INTERNAL_NOTE_PATTERNS:
        cleaned = pattern.sub("", cleaned).strip()
    return cleaned


def format_enhanced_prompt_for_display(enhanced_prompt: str) -> str:
    """Return enhanced prompt text suitable for the UI viewer."""
    return sanitize_enhanced_prompt(enhanced_prompt)


def _format_conversation_context(conversation_history: list[dict]) -> str:
    if not conversation_history:
        return ""
    lines: list[str] = []
    for msg in conversation_history:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _build_system_prompt(persona: str, task_type: str, complexity_level: str) -> str:
    base = (
        f"You are a {persona}. Preserve the user's intent exactly. "
        "Do not invent facts, data, or claims the user did not provide."
    )
    if complexity_level == "simple":
        return f"{base} Answer clearly and concisely."
    if complexity_level == "medium":
        return (
            f"{base} Organize the response with clear structure and practical clarity."
        )
    return (
        f"{base} Address assumptions, constraints, and trade-offs explicitly. "
        f"Use a rigorous, step-by-step approach appropriate for {task_type.replace('_', ' ')} tasks."
    )


def _enhance_simple(original: str, output_format: str) -> str:
    """Minimal enhancement for short/simple prompts."""
    return original.strip()


def _enhance_medium(original: str, output_format: str, task_type: str) -> str:
    """Add structure and clarity without heavy scaffolding."""
    prompt = original.strip()
    return (
        f"{prompt}\n\n"
        f"Please respond with clear structure. Preferred output format: {output_format}."
    )


def _enhance_complex(
    original: str,
    output_format: str,
    task_type: str,
    conversation_history: list[dict],
) -> str:
    """Full enhancement for complex prompts."""
    sections = [original.strip()]

    if conversation_history:
        context_block = _format_conversation_context(conversation_history)
        sections.append(
            "Conversation context (use only what appears below — do not invent details):\n"
            f"{context_block}"
        )

    sections.append(
        "Enhancement requirements:\n"
        "- State assumptions explicitly when information is missing\n"
        "- Note relevant constraints and trade-offs\n"
        f"- Follow this output format: {output_format}\n"
        "- Use a step-by-step approach where appropriate"
    )

    if task_type == "coding":
        sections.append(
            "- Include clean, readable code with helpful comments and edge-case notes"
        )
    elif task_type == "business":
        sections.append(
            "- Use professional business language with an executive-ready structure"
        )
    elif task_type == "data_analysis":
        sections.append(
            "- Highlight metrics, patterns, and actionable data-driven recommendations"
        )

    return "\n\n".join(sections)


def _build_rule_based_analysis(
    original_prompt: str,
    task_type: str,
    difficulty: str,
    risk_level: str,
    conversation_history: list[dict],
) -> PromptAnalysis:
    """Rule-based v2 enhancement — no API call."""
    prompt = (original_prompt or "").strip()
    normalized_task = normalize_task_type(task_type)
    score = compute_complexity_score(prompt, normalized_task, difficulty=difficulty)
    level = complexity_level_from_score(score)
    persona = select_persona(normalized_task)
    output_format = select_output_format(normalized_task)
    strategy = select_enhancement_strategy(normalized_task, level)

    if level == "simple":
        enhanced = _enhance_simple(prompt, output_format)
        reason = "Simple prompt — applied minimal clarity enhancement."
    elif level == "medium":
        enhanced = _enhance_medium(prompt, output_format, normalized_task)
        reason = "Medium complexity — added structure and output format guidance."
    else:
        enhanced = _enhance_complex(
            prompt, output_format, normalized_task, conversation_history
        )
        reason = (
            "Complex prompt — added assumptions, constraints, output format, "
            "and step-by-step requirements."
        )

    if conversation_history and level != "complex":
        reason += f" Considered {len(conversation_history)} prior message(s)."

    return PromptAnalysis(
        original_prompt=prompt,
        task_type=normalized_task,
        complexity_score=score,
        complexity_level=level,
        persona=persona,
        output_format=output_format,
        enhancement_strategy=strategy,
        enhanced_prompt=sanitize_enhanced_prompt(enhanced),
        system_prompt=_build_system_prompt(persona, normalized_task, level),
        enhancement_reason=reason,
        enhancement_method="rule_fallback",
    )


def _extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return json.loads(cleaned)


def _build_ai_messages(
    original_prompt: str,
    task_type: str,
    complexity_score: int,
    complexity_level: str,
    persona: str,
    output_format: str,
    enhancement_strategy: str,
    conversation_history: list[dict],
) -> list[dict]:
    context_block = _format_conversation_context(conversation_history)
    system_prompt = f"""You are the Prompt Intelligence Engine for an LLM routing system.

Analyze the user request, then produce an enhanced prompt for a downstream model.

Respond with JSON ONLY — no markdown fences, no extra text.

Required JSON schema:
{{
  "enhanced_prompt": "<clean user-facing prompt — NO internal notes or bracketed scaffolding>",
  "system_prompt": "<system message for the downstream model>",
  "enhancement_reason": "<one short sentence explaining what you improved>"
}}

Context for this request:
- Task type: {task_type}
- Complexity score: {complexity_score} (0-100)
- Complexity level: {complexity_level}
- Persona: {persona}
- Output format: {output_format}
- Enhancement strategy: {enhancement_strategy}

Rules:
- Preserve the user's original meaning and intent exactly.
- Do NOT add facts, data, or claims the user did not provide.
- Do NOT include internal notes like "[Original user request — preserve this intent: ...]".
- For simple prompts, make only minimal improvements.
- For medium prompts, add structure and clarity.
- For complex prompts, add assumptions, constraints, output format, and step-by-step guidance.
- enhanced_prompt must read like a polished user request, not internal instructions to the router.
"""

    user_parts = [f"Original user request:\n{original_prompt.strip()}"]
    if context_block:
        user_parts.insert(
            0,
            "Conversation context (reference only):\n" + context_block + "\n",
        )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


def _enhance_with_ai(
    original_prompt: str,
    task_type: str,
    difficulty: str,
    risk_level: str,
    conversation_history: list[dict],
) -> PromptAnalysis:
    import litellm

    normalized_task = normalize_task_type(task_type)
    score = compute_complexity_score(
        original_prompt, normalized_task, difficulty=difficulty
    )
    level = complexity_level_from_score(score)
    persona = select_persona(normalized_task)
    output_format = select_output_format(normalized_task)
    strategy = select_enhancement_strategy(normalized_task, level)

    litellm_model = _to_litellm_model(get_auxiliary_model("enhancer"))
    messages = _build_ai_messages(
        original_prompt,
        normalized_task,
        score,
        level,
        persona,
        output_format,
        strategy,
        conversation_history,
    )

    logger.info(
        "Prompt Intelligence v2 | model=%s | task=%s | level=%s",
        litellm_model,
        normalized_task,
        level,
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
        raise ValueError("AI enhancer returned empty response")

    parsed = _extract_json_object(text)
    enhanced = sanitize_enhanced_prompt(str(parsed.get("enhanced_prompt", "")).strip())
    system = str(parsed.get("system_prompt", "")).strip()
    reason = str(parsed.get("enhancement_reason", "")).strip()

    if not enhanced:
        raise ValueError("AI enhancer returned empty enhanced_prompt")

    if not system:
        system = _build_system_prompt(persona, normalized_task, level)
    if not reason:
        reason = "AI prompt intelligence improved clarity and task-specific guidance."

    return PromptAnalysis(
        original_prompt=original_prompt.strip(),
        task_type=normalized_task,
        complexity_score=score,
        complexity_level=level,
        persona=persona,
        output_format=output_format,
        enhancement_strategy=strategy,
        enhanced_prompt=enhanced,
        system_prompt=system,
        enhancement_reason=reason,
        enhancement_method="ai",
    )


def _to_litellm_model(groq_model: str) -> str:
    if groq_model.startswith("groq/"):
        return groq_model
    return f"groq/{groq_model}"


def _has_groq_key() -> bool:
    return bool(os.getenv(GROQ_ENV_KEY, "").strip())


def analyze_and_enhance(
    original_prompt: str,
    task_type: str,
    difficulty: str = "medium",
    risk_level: str = "low",
    conversation_history: list[dict] | None = None,
) -> PromptAnalysis:
    """
    Analyze a user prompt, then enhance it using task type, complexity, and persona.

    1. Normalize task type and compute complexity (0–100).
    2. Select persona, output format, and enhancement strategy.
    3. If GROQ_API_KEY is set → AI enhancement; else rule-based v2.
    """
    history = conversation_history or []
    prompt = sanitize_enhanced_prompt((original_prompt or "").strip())

    if not prompt:
        analysis = _build_rule_based_analysis(
            "", task_type, difficulty, risk_level, history
        )
        analysis.enhancement_reason = "Empty prompt — used minimal rule fallback."
        return analysis

    if _has_groq_key():
        try:
            return _enhance_with_ai(
                prompt, task_type, difficulty, risk_level, history
            )
        except Exception as exc:
            logger.warning(
                "Prompt Intelligence AI failed (%s) — using rule fallback",
                exc,
            )
    else:
        logger.info("%s not set — using rule-based Prompt Intelligence v2", GROQ_ENV_KEY)

    return _build_rule_based_analysis(
        prompt, task_type, difficulty, risk_level, history
    )


def build_disabled_analysis(
    original_prompt: str,
    task_type: str,
    difficulty: str = "medium",
) -> PromptAnalysis:
    """Return a PromptAnalysis when enhancement is turned off by the user."""
    normalized_task = normalize_task_type(task_type)
    score = compute_complexity_score(
        original_prompt, normalized_task, difficulty=difficulty
    )
    level = complexity_level_from_score(score)
    prompt = (original_prompt or "").strip()

    return PromptAnalysis(
        original_prompt=prompt,
        task_type=normalized_task,
        complexity_score=score,
        complexity_level=level,
        persona=select_persona(normalized_task),
        output_format=select_output_format(normalized_task),
        enhancement_strategy="disabled",
        enhanced_prompt=prompt,
        system_prompt="",
        enhancement_reason="Prompt enhancement disabled by user",
        enhancement_method="disabled",
    )
