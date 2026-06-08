"""
Router Engine — picks the best model for a given prompt context.

Routing rules (MVP):
  - coding & data_analysis  → standard tier (needs stronger reasoning)
  - creative_writing          → economy tier (cheaper models are fine)
  - summarization & translation → economy tier (structured, simpler tasks)
  - general_qa                → depends on prompt length and confidence
  - long prompts              → bias toward economy to save money

Later you can add latency tracking, user budgets, and A/B quality scores.
"""

from dataclasses import dataclass

from services.context_builder import PromptContext


@dataclass
class RoutingDecision:
    """The router's choice and why it made that choice."""

    model_id: str
    model_label: str
    reason: str


# Maps task types to a preferred model and a human-readable reason
_ROUTING_TABLE: dict[str, tuple[str, str]] = {
    "coding": (
        "gpt-4o-mini",
        "Coding tasks benefit from stronger reasoning; GPT-4o Mini balances "
        "quality and cost.",
    ),
    "data_analysis": (
        "gpt-4o-mini",
        "Data analysis needs reliable logic; standard tier is a good fit.",
    ),
    "summarization": (
        "claude-3-haiku",
        "Summarization is a structured task — a fast economy model works well.",
    ),
    "creative_writing": (
        "gemini-flash",
        "Creative writing doesn't need premium reasoning; Gemini Flash is "
        "cost-effective and fast.",
    ),
    "translation": (
        "claude-3-haiku",
        "Translation is pattern-based; economy models handle it efficiently.",
    ),
    "general_qa": (
        "gemini-flash",
        "Simple Q&A can use an economy model unless the prompt is complex.",
    ),
}

# Friendly display names (imported from cost_tracker pricing labels)
_MODEL_LABELS: dict[str, str] = {
    "gpt-4o": "GPT-4o (Premium)",
    "gpt-4o-mini": "GPT-4o Mini (Standard)",
    "claude-3-haiku": "Claude 3 Haiku (Economy)",
    "gemini-flash": "Gemini Flash (Economy)",
}


def route(context: PromptContext) -> RoutingDecision:
    """
    Select the best model for this prompt.

    Overrides:
      - Very long prompts → force economy model to cut costs
      - Low-confidence general_qa with short prompt → economy is fine
      - High-confidence complex coding with long prompt → still standard
    """
    task_type = context.task_type

    # Default routing from the table
    model_id, reason = _ROUTING_TABLE.get(
        task_type,
        ("gemini-flash", "Unknown task type — defaulting to economy model."),
    )

    # Override: very long prompts should not use premium-tier models
    if context.is_long_prompt and model_id == "gpt-4o-mini":
        model_id = "claude-3-haiku"
        reason = (
            "Prompt is long (>500 tokens est.); switched to economy model "
            "to reduce cost while keeping acceptable quality."
        )

    # Override: short, low-confidence Q&A → cheapest option
    if (
        task_type == "general_qa"
        and context.confidence < 0.6
        and not context.is_long_prompt
    ):
        model_id = "gemini-flash"
        reason = (
            "Short, simple question detected — Gemini Flash is fast and cheap."
        )

    return RoutingDecision(
        model_id=model_id,
        model_label=_MODEL_LABELS.get(model_id, model_id),
        reason=reason,
    )
