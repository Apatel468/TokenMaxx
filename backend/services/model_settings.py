"""
Model Settings — per-model enable/disable preferences stored in SQLite.

The catalog is sourced from groq_models (Groq API + model_registry.py),
not from hardcoded model lists.
"""

from sqlalchemy.orm import Session

from config.model_registry import cost_per_1k_tokens, tier_for_model
from database import ModelSetting
from services.config_loader import get_allowed_task_types, resolve_task_key
from services.groq_models import get_model_record, get_routable_model_ids, get_routable_models
from services.model_scorer import score_candidates

FALLBACK_BADGE = "Preferred model disabled — fallback used"


def get_unique_routable_model_ids() -> list[str]:
    """Return all chat-routable Groq model ids (API + registry)."""
    return get_routable_model_ids()


def seed_model_settings(db: Session) -> None:
    """Ensure every routable model has a settings row (default: enabled)."""
    for model_id in get_unique_routable_model_ids():
        existing = (
            db.query(ModelSetting)
            .filter(ModelSetting.model_id == model_id)
            .first()
        )
        if not existing:
            db.add(ModelSetting(model_id=model_id, enabled=True))
    db.commit()


def get_enabled_model_ids(db: Session) -> set[str]:
    """Return model ids the router is allowed to use."""
    seed_model_settings(db)
    rows = db.query(ModelSetting).filter(ModelSetting.enabled.is_(True)).all()
    return {row.model_id for row in rows}


def is_model_enabled(db: Session, model_id: str) -> bool:
    seed_model_settings(db)
    row = db.query(ModelSetting).filter(ModelSetting.model_id == model_id).first()
    return bool(row and row.enabled)


def _best_tasks_for_model(model_id: str) -> list[str]:
    """Task types where this model scores in the top tier among all routable models."""
    catalog = get_routable_models()
    task_types = get_allowed_task_types()
    best_for: list[str] = []

    for task in task_types:
        scored = score_candidates(task, catalog)
        if not scored:
            continue
        top_score = scored[0].score
        for candidate in scored[:3]:
            if candidate.model_id == model_id and candidate.score >= top_score - 2:
                best_for.append(task)
                break

    return best_for or [resolve_task_key("general_qa")]


def list_model_controls(db: Session) -> list[dict]:
    """Return catalog rows for the Model Controls UI."""
    seed_model_settings(db)
    rows_by_id = {row.model_id: row for row in db.query(ModelSetting).all()}

    results: list[dict] = []
    for record in get_routable_models():
        model_id = record.model_id
        meta = record.metadata
        row = rows_by_id.get(model_id)
        cost_in, cost_out = cost_per_1k_tokens(model_id, meta)

        results.append(
            {
                "model_id": model_id,
                "name": meta["model_name"],
                "provider": meta["provider"],
                "tier": tier_for_model(model_id, meta),
                "task_types": _best_tasks_for_model(model_id),
                "enabled": bool(row.enabled if row else True),
                "cost_per_1k_input": cost_in,
                "cost_per_1k_output": cost_out,
            }
        )
    return results


def update_model_controls(db: Session, updates: list[dict]) -> list[dict]:
    """Apply enable/disable toggles from the settings UI."""
    seed_model_settings(db)
    known_ids = set(get_unique_routable_model_ids())

    for item in updates:
        model_id = item["model_id"]
        if model_id not in known_ids:
            continue
        row = (
            db.query(ModelSetting)
            .filter(ModelSetting.model_id == model_id)
            .first()
        )
        if row:
            row.enabled = bool(item["enabled"])

    db.commit()
    return list_model_controls(db)


class NoModelsEnabledError(Exception):
    """Raised when routing cannot proceed because every model is disabled."""
