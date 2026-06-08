"""
Cost Tracker — estimates token usage and dollar costs.

Pricing numbers are illustrative (based on common public rates).
We always compare against a single "premium" baseline (gpt-4o) so
the savings percentage is easy to understand.
"""

from dataclasses import dataclass

from services.context_builder import PromptContext
from services.model_clients import ModelResponse


# Cost per 1,000 tokens (USD) — input and output priced separately
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {
        "input": 0.005,
        "output": 0.015,
        "label": "GPT-4o (Premium)",
    },
    "gpt-4o-mini": {
        "input": 0.00015,
        "output": 0.0006,
        "label": "GPT-4o Mini (Standard)",
    },
    "claude-3-haiku": {
        "input": 0.00025,
        "output": 0.00125,
        "label": "Claude 3 Haiku (Economy)",
    },
    "gemini-flash": {
        "input": 0.000075,
        "output": 0.0003,
        "label": "Gemini Flash (Economy)",
    },
}

# The expensive model we compare everything against
PREMIUM_MODEL_ID = "gpt-4o"


@dataclass
class CostEstimate:
    """Cost breakdown for one chat request."""

    actual_cost: float
    premium_cost: float
    savings_percentage: float
    input_tokens: int
    output_tokens: int


def _calculate_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Compute USD cost for a given model and token counts."""
    pricing = MODEL_PRICING[model_id]
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def estimate_costs(
    selected_model_id: str,
    context: PromptContext,
    model_response: ModelResponse,
) -> CostEstimate:
    """
    Compare the cost of the chosen model vs. always using premium.

    Savings % = (premium_cost - actual_cost) / premium_cost * 100
    If premium is cheaper (shouldn't happen), savings is 0.
    """
    input_tokens = context.estimated_input_tokens
    output_tokens = model_response.estimated_output_tokens

    actual_cost = _calculate_cost(selected_model_id, input_tokens, output_tokens)
    premium_cost = _calculate_cost(PREMIUM_MODEL_ID, input_tokens, output_tokens)

    if premium_cost > 0 and actual_cost < premium_cost:
        savings = ((premium_cost - actual_cost) / premium_cost) * 100
    else:
        savings = 0.0

    return CostEstimate(
        actual_cost=actual_cost,
        premium_cost=premium_cost,
        savings_percentage=round(savings, 2),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
