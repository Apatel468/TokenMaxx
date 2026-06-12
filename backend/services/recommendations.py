"""
Top model recommendations — enrich router scores for the regenerate UI.

Returns metadata only; no LLM calls until the user clicks a model.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from config.model_registry import cost_per_1k_tokens, get_registry_entry
from services.context_builder import PromptContext
from services.groq_models import get_routable_models
from services.model_settings import get_model_disabled_reason

_ESTIMATED_OUTPUT_TOKENS = 150


def _estimate_cost(model_id: str, input_tokens: int) -> float:
    meta = get_registry_entry(model_id) or {}
    cost_in, cost_out = cost_per_1k_tokens(model_id, meta or None)
    input_cost = (input_tokens / 1000) * cost_in
    output_cost = (_ESTIMATED_OUTPUT_TOKENS / 1000) * cost_out
    return round(input_cost + output_cost, 6)


def _estimate_latency(model_id: str) -> float:
    meta = get_registry_entry(model_id) or {}
    return float(meta.get("avg_latency_ms", 800))


def build_top_recommendations(
    db: Session,
    user_id: int,
    scored_candidates: list[dict],
    context: PromptContext,
    *,
    limit: int = 5,
) -> list[dict]:
    """
    Top N ranked models with cost/latency estimates and availability flags.

    Uses pre-computed router scores — does not call any LLM.
    """
    catalog_ids = {r.model_id for r in get_routable_models()}
    input_tokens = max(context.estimated_input_tokens, 1)
    results: list[dict] = []

    for candidate in scored_candidates[:limit]:
        model_id = candidate["model_id"]
        if model_id not in catalog_ids:
            continue
        disabled_reason = get_model_disabled_reason(db, user_id, model_id)
        available = disabled_reason is None
        results.append(
            {
                "model_id": model_id,
                "provider": candidate.get("provider", "groq"),
                "ranking_score": float(candidate.get("score", 0)),
                "estimated_cost": _estimate_cost(model_id, input_tokens),
                "estimated_latency": _estimate_latency(model_id),
                "available": available,
                "disabled_reason": disabled_reason or "",
            }
        )

    return results
