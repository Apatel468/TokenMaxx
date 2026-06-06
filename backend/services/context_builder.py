"""
Context Builder — prepares metadata about the prompt before routing.

Phase 3A: also accounts for prior messages when estimating token usage
and passes full message history to the model client.
"""

from dataclasses import dataclass, field

from services.prompt_analyzer import AnalysisResult


@dataclass
class PromptContext:
    """Everything the router and model client need for one turn."""

    prompt: str
    task_type: str
    confidence: float
    estimated_input_tokens: int
    is_long_prompt: bool
    keywords_matched: list[str]
    # Full chat history including the new user message (for LiteLLM)
    message_history: list[dict] = field(default_factory=list)


_CHARS_PER_TOKEN = 4
_LONG_PROMPT_TOKEN_THRESHOLD = 500


def build_context(
    prompt: str,
    analysis: AnalysisResult,
    prior_messages: list[dict] | None = None,
) -> PromptContext:
    """
    Build context for routing and model calls.

    Args:
        prompt: The user's latest message.
        analysis: Task classification for this message.
        prior_messages: Earlier user/assistant turns (without the new prompt).
    """
    prior = prior_messages or []
    full_history = prior + [{"role": "user", "content": prompt}]

    # Estimate tokens across the entire conversation + new message
    total_chars = sum(len(m["content"]) for m in full_history)
    estimated_tokens = max(total_chars // _CHARS_PER_TOKEN, 1)

    return PromptContext(
        prompt=prompt,
        task_type=analysis.task_type,
        confidence=analysis.confidence,
        estimated_input_tokens=estimated_tokens,
        is_long_prompt=estimated_tokens > _LONG_PROMPT_TOKEN_THRESHOLD,
        keywords_matched=analysis.keywords_matched,
        message_history=full_history,
    )
