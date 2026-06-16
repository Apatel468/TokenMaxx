"""
Prompt Enhancer — delegates to Prompt Intelligence Engine v2.

Kept for backward-compatible imports across the codebase.
"""

from services.prompt_intelligence import (
    PromptAnalysis,
    analyze_and_enhance,
    build_disabled_analysis,
    format_enhanced_prompt_for_display,
    sanitize_enhanced_prompt,
)

# Backward-compatible alias used by older imports.
EnhancementResult = PromptAnalysis


def enhance_prompt(
    original_prompt: str,
    task_type: str,
    difficulty: str,
    risk_level: str,
    conversation_history: list[dict] | None = None,
) -> PromptAnalysis:
    """Enhance a user prompt via Prompt Intelligence Engine v2."""
    return analyze_and_enhance(
        original_prompt=original_prompt,
        task_type=task_type,
        difficulty=difficulty,
        risk_level=risk_level,
        conversation_history=conversation_history,
    )
