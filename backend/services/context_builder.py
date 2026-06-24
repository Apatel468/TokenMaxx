"""
Context Builder — prepares metadata about the prompt before routing (Phase 4).

Pipeline inside build_context:
  1. Prompt Intelligence Engine v2 — analyze then enhance (or skip if disabled)
  2. Build message_history for LiteLLM (prior turns + enhanced latest message)
  3. Estimate token usage for cost tracking
"""

from dataclasses import dataclass, field

from services.prompt_analyzer import AnalysisResult
from services.prompt_intelligence import (
    PromptAnalysis,
    analyze_and_enhance,
    build_disabled_analysis,
)


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
    prompt_analysis: PromptAnalysis | None = None
    # Full chat history for LiteLLM: prior messages + enhanced latest user turn
    message_history: list[dict] = field(default_factory=list)
    # Phase 2 RAG — document retrieval metadata (injected into system_prompt)
    rag_used: bool = False
    retrieved_chunk_count: int = 0
    source_documents: list[int] = field(default_factory=list)
    source_filenames: list[str] = field(default_factory=list)
    # Sentiment-aware response styling (injected into system_prompt)
    sentiment_label: str | None = None
    sentiment_style_applied: bool = False
    sentiment_result: object | None = None  # SentimentResult when resolved
    # Web research — live search + scrape metadata (injected into system_prompt)
    web_research_used: bool = False
    web_search_query: str = ""
    web_search_provider: str = ""
    web_scrape_duration_ms: float = 0.0
    web_sources: list = field(default_factory=list)  # WebSource objects
    web_research_error: str = ""
    web_research_direct_urls: bool = False
    web_fallback_used: bool = False
    web_fallback_reason: str = ""
    web_original_blocked_urls: list = field(default_factory=list)


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
        prompt_analysis = analyze_and_enhance(
            original_prompt=prompt,
            task_type=analysis.task_type,
            difficulty=analysis.difficulty,
            risk_level=analysis.risk_level,
            conversation_history=prior,
        )
    else:
        prompt_analysis = build_disabled_analysis(
            original_prompt=prompt,
            task_type=analysis.task_type,
            difficulty=analysis.difficulty,
        )

    enhanced_text = prompt_analysis.enhanced_prompt
    system_text = prompt_analysis.system_prompt or None
    reason = prompt_analysis.enhancement_reason
    method = prompt_analysis.enhancement_method

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
        prompt_analysis=prompt_analysis,
        message_history=full_history,
    )
