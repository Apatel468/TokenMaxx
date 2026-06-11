"""
Router Engine — scores all enabled Groq models and picks the best fit.

Routing is fully dynamic:
  1. Load routable models from groq_models (API + model_registry.py)
  2. Filter to user-enabled models (SQLite model_settings)
  3. Score each candidate via model_scorer.py
  4. Pick highest score; if preferred (top) is disabled, use next enabled

To add a new Groq model: edit backend/config/model_registry.py only.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from services.config_loader import get_task_profile, resolve_task_key
from services.context_builder import PromptContext
from services.groq_models import GroqModelRecord, get_routable_models
from services.model_scorer import CandidateScore, score_candidates
from services.model_settings import (
    FALLBACK_BADGE,
    NoModelsEnabledError,
    get_enabled_model_ids,
)


@dataclass
class RoutingDecision:
    """The router's choice, score breakdown, and all candidates considered."""

    model_id: str
    model_label: str
    reason: str
    groq_model: str
    provider: str
    score: float = 0.0
    candidate_models: list[dict] = field(default_factory=list)
    preferred_model_id: str = ""
    used_fallback: bool = False
    fallback_message: str = ""


def _records_for_ids(
    catalog: list[GroqModelRecord], model_ids: set[str]
) -> list[GroqModelRecord]:
    return [r for r in catalog if r.model_id in model_ids]


def route(context: PromptContext, db: Session) -> RoutingDecision:
    """
    Score every enabled routable Groq model and select the best.

    Raises NoModelsEnabledError when every model is toggled off.
    """
    catalog = get_routable_models()
    if not catalog:
        raise NoModelsEnabledError(
            "No routable Groq models in catalog. Check model_registry.py "
            "and your Groq API key."
        )

    enabled_ids = get_enabled_model_ids(db)
    if not enabled_ids:
        raise NoModelsEnabledError(
            "No models are enabled. Open Model Controls and enable at least one model."
        )

    enabled_catalog = _records_for_ids(catalog, enabled_ids)
    if not enabled_catalog:
        raise NoModelsEnabledError(
            "No enabled models match the Groq catalog. "
            "Enable routable models in Model Controls."
        )

    # Score ALL routable models (including disabled) to find theoretical preferred
    all_scored = score_candidates(context.task_type, catalog)
    candidate_dicts = [c.to_dict() for c in all_scored]

    preferred_id = all_scored[0].model_id if all_scored else ""
    enabled_scored = [c for c in all_scored if c.model_id in enabled_ids]

    if not enabled_scored:
        raise NoModelsEnabledError(
            "No models are enabled. Open Model Controls and enable at least one model."
        )

    winner = enabled_scored[0]
    used_fallback = winner.model_id != preferred_id
    task_key = resolve_task_key(context.task_type)
    profile = get_task_profile(context.task_type)

    if used_fallback:
        reason = (
            f"Preferred model ({preferred_id}) is disabled. "
            f"Scored {winner.model_id} highest among enabled models "
            f"(score {winner.score}) for {task_key} — {profile.get('description', '')}"
        )
        fallback_message = FALLBACK_BADGE
    else:
        reason = (
            f"Scored {winner.model_id} highest (score {winner.score}) for "
            f"{task_key} — {profile.get('description', '')}"
        )
        fallback_message = ""

    record = next(r for r in catalog if r.model_id == winner.model_id)
    provider = record.metadata["provider"]
    model_label = f"Groq / {winner.model_id}"

    return RoutingDecision(
        model_id=winner.model_id,
        model_label=model_label,
        reason=reason,
        groq_model=winner.model_id,
        provider=provider,
        score=winner.score,
        candidate_models=candidate_dicts,
        preferred_model_id=preferred_id,
        used_fallback=used_fallback,
        fallback_message=fallback_message,
    )


__all__ = ["RoutingDecision", "route", "NoModelsEnabledError"]
