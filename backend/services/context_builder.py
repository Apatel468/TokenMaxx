"""
Context Builder — prepares metadata about the prompt before routing (Phase 4).

Pipeline inside build_context:
  1. Call prompt_enhancer.enhance_prompt() — AI agent (Groq) or rule fallback
  2. Build message_history for LiteLLM (prior turns + enhanced latest message)
  3. Estimate token usage for cost tracking
"""

from dataclasses import dataclass, field

from services.prompt_analyzer import AnalysisResult
from services.prompt_enhancer import enhance_prompt


@dataclass
class PromptContext:
    """Everything the router and model client need for one turn."""

    prompt: str  # Original user text (unchanged)
    task_type: str
    confidence: float
    estimated_input_tokens: int
    is_long_prompt: bool
    keywords_matched: list[str]
    # Phase 4 — prompt engineering outputs
    enhanced_prompt: str = ""
    system_prompt: str | None = None
    enhancement_reason: str = ""
    enhancement_method: str = "rule_fallback"  # "ai", "rule_fallback", or "disabled"
    # Full chat history for LiteLLM: prior messages + enhanced latest user turn
    message_history: list[dict] = field(default_factory=list)


_CHARS_PER_TOKEN = 4
_LONG_PROMPT_TOKEN_THRESHOLD = 500


def build_context(
    prompt: str,
    analysis: AnalysisResult,
    prior_messages: list[dict] | None = None,
    *,
    enhance_prompt_enabled: bool = True,
) -> PromptContext:
    """
    Build context for routing and model calls.

    Args:
        prompt: The user's latest message (stored as-is in the database).
        analysis: Task classification from prompt_analyzer.
        prior_messages: Earlier user/assistant turns (without the new prompt).
        enhance_prompt_enabled: When False, skip enhancement entirely.
    """
    prior = prior_messages or []

    if enhance_prompt_enabled:
        enhancement = enhance_prompt(
            original_prompt=prompt,
            task_type=analysis.task_type,
            difficulty=analysis.difficulty,
            risk_level=analysis.risk_level,
            conversation_history=prior,
        )
        enhanced_text = enhancement.enhanced_prompt
        system_text = enhancement.system_prompt
        reason = enhancement.enhancement_reason
        method = enhancement.enhancement_method
    else:
        enhanced_text = prompt
        system_text = None
        reason = "Prompt enhancement disabled by user"
        method = "disabled"

    # LiteLLM history: keep prior turns original; only the new turn may be enhanced
    full_history = prior + [{"role": "user", "content": enhanced_text}]

    system_len = len(system_text) if system_text else 0
    total_chars = system_len + sum(len(m["content"]) for m in full_history)
    estimated_tokens = max(total_chars // _CHARS_PER_TOKEN, 1)

    return PromptContext(
        prompt=prompt,
        task_type=analysis.task_type,
        confidence=analysis.confidence,
        estimated_input_tokens=estimated_tokens,
        is_long_prompt=estimated_tokens > _LONG_PROMPT_TOKEN_THRESHOLD,
        keywords_matched=analysis.keywords_matched,
        enhanced_prompt=enhanced_text,
        system_prompt=system_text,
        enhancement_reason=reason,
        enhancement_method=method,
        message_history=full_history,
    )
