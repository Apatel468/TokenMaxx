"""
Router Engine — picks the best Groq model for a given prompt context.

Routing rules live in config/models.yaml (not hard-coded here).
This file only reads the YAML and returns a RoutingDecision.
"""

from dataclasses import dataclass

from services.config_loader import get_route_for_task
from services.context_builder import PromptContext


@dataclass
class RoutingDecision:
    """The router's choice and why it made that choice."""

    model_id: str       # Groq model name (used for cost lookup)
    model_label: str    # Friendly name shown in the API response
    reason: str         # Why this model was picked (from YAML)
    groq_model: str     # Model string sent to LiteLLM
    provider: str       # Always "groq" for Phase 2


def route(context: PromptContext) -> RoutingDecision:
    """
    Select the best Groq model for this prompt's task type.

    Steps:
      1. Look up task_type in config/models.yaml
      2. Return provider, model, and reason from that entry
    """
    route_config = get_route_for_task(context.task_type)

    groq_model = route_config["model"]
    provider = route_config["provider"]
    reason = route_config["reason"]

    model_label = f"Groq / {groq_model}"

    return RoutingDecision(
        model_id=groq_model,
        model_label=model_label,
        reason=reason,
        groq_model=groq_model,
        provider=provider,
    )
