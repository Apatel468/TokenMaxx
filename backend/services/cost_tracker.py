"""
Cost Tracker — estimates token usage and dollar costs.

Pricing is loaded from config/model_registry.py.
Savings compare each Groq model vs. the premium baseline (GPT-4o) in YAML.
"""

import logging
from dataclasses import dataclass

from config.model_registry import cost_per_1k_tokens
from services.config_loader import get_auxiliary_model, get_premium_baseline
from services.context_builder import PromptContext
from services.model_clients import ModelResponse

logger = logging.getLogger(__name__)


@dataclass
class CostEstimate:
    """Cost breakdown for one chat request."""

    actual_cost: float
    premium_cost: float
    savings_percentage: float
    input_tokens: int
    output_tokens: int


def _calculate_cost(
    input_per_1k: float,
    output_per_1k: float,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Compute USD cost from per-1k rates and token counts."""
    input_cost = (input_tokens / 1000) * input_per_1k
    output_cost = (output_tokens / 1000) * output_per_1k
    return round(input_cost + output_cost, 6)


def _get_model_rates(model_id: str) -> tuple[float, float]:
    """Look up per-1K token rates from model_registry.py."""
    return cost_per_1k_tokens(model_id)


def estimate_costs(
    selected_model_id: str,
    context: PromptContext,
    model_response: ModelResponse,
) -> CostEstimate:
    """
    Compare Groq model cost vs. premium baseline from YAML.

    Uses real token counts from LiteLLM when available; otherwise estimates.
    """
    input_tokens = model_response.input_tokens or context.estimated_input_tokens
    output_tokens = model_response.estimated_output_tokens

    groq_in, groq_out = _get_model_rates(selected_model_id)
    actual_cost = _calculate_cost(groq_in, groq_out, input_tokens, output_tokens)

    baseline = get_premium_baseline()
    premium_cost = _calculate_cost(
        baseline.get("input_per_1k", 0.005),
        baseline.get("output_per_1k", 0.015),
        input_tokens,
        output_tokens,
    )

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


_CHARS_PER_TOKEN = 4
_ESTIMATED_ENHANCER_OUTPUT_TOKENS = 120


def estimate_enhancement_cost_saved(prompt: str) -> float:
    """
    Estimate USD saved by skipping the enhancer Groq call.

    Uses the auxiliary enhancer model rates and prompt-length token estimate.
    """
    enhancer_id = get_auxiliary_model("enhancer")
    input_per_1k, output_per_1k = _get_model_rates(enhancer_id)
    input_tokens = max(len(prompt) // _CHARS_PER_TOKEN, 1)
    return _calculate_cost(
        input_per_1k,
        output_per_1k,
        input_tokens,
        _ESTIMATED_ENHANCER_OUTPUT_TOKENS,
    )


def log_request_metrics(
    model_id: str,
    task_type: str,
    model_response: ModelResponse,
    costs: CostEstimate,
) -> None:
    """Log model, tokens, latency, and estimated cost for each chat request."""
    logger.info(
        "Request metrics | groq_model=%s | litellm_model=%s | mock=%s | "
        "task=%s | input_tokens=%d | output_tokens=%d | "
        "latency_ms=%.1f | actual_cost_usd=%.6f | premium_cost_usd=%.6f | "
        "savings_pct=%.1f",
        model_id,
        model_response.litellm_model,
        model_response.is_mock,
        task_type,
        costs.input_tokens,
        costs.output_tokens,
        model_response.latency_ms,
        costs.actual_cost,
        costs.premium_cost,
        costs.savings_percentage,
    )
