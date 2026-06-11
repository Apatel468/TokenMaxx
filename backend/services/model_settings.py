"""
Model Settings — admin (org-wide) and per-user enable/disable preferences.

Effective routing availability:
    model_enabled = admin_enabled AND user_enabled

Missing DB rows default to enabled=True. Existing rows with enabled=False
are never overridden on load.
"""

from sqlalchemy.orm import Session

from config.model_registry import cost_per_1k_tokens, tier_for_model
from database import AdminModelSetting, UserModelSetting
from services.config_loader import get_allowed_task_types, resolve_task_key
from services.groq_models import get_routable_model_ids, get_routable_models
from services.model_scorer import score_candidates

FALLBACK_BADGE_ADMIN = "Preferred model disabled by admin — fallback used"
FALLBACK_BADGE_USER = (
    "Preferred model disabled in your preferences — fallback used"
)
FALLBACK_BADGE = FALLBACK_BADGE_ADMIN


def get_unique_routable_model_ids() -> list[str]:
    return get_routable_model_ids()


def seed_admin_model_settings(db: Session) -> None:
    """Insert admin rows only for models that have no row yet (default enabled)."""
    for model_id in get_unique_routable_model_ids():
        existing = (
            db.query(AdminModelSetting)
            .filter(AdminModelSetting.model_id == model_id)
            .first()
        )
        if not existing:
            db.add(AdminModelSetting(model_id=model_id, enabled=True))
    db.commit()


seed_model_settings = seed_admin_model_settings


def _admin_enabled_map(db: Session) -> dict[str, bool]:
    """Read admin flags from DB; default True only when row is missing."""
    seed_admin_model_settings(db)
    rows = {
        row.model_id: row.enabled
        for row in db.query(AdminModelSetting).all()
    }
    return {
        model_id: bool(rows[model_id]) if model_id in rows else True
        for model_id in get_unique_routable_model_ids()
    }


def _user_enabled_map(db: Session, user_id: int) -> dict[str, bool]:
    """Read user flags from DB; default True only when row is missing."""
    rows = {
        row.model_id: row.enabled
        for row in db.query(UserModelSetting)
        .filter(UserModelSetting.user_id == user_id)
        .all()
    }
    return {
        model_id: bool(rows[model_id]) if model_id in rows else True
        for model_id in get_unique_routable_model_ids()
    }


def _upsert_admin_setting(db: Session, model_id: str, enabled: bool) -> None:
    row = (
        db.query(AdminModelSetting)
        .filter(AdminModelSetting.model_id == model_id)
        .first()
    )
    if row:
        row.enabled = enabled
    else:
        db.add(AdminModelSetting(model_id=model_id, enabled=enabled))


def _upsert_user_setting(
    db: Session, user_id: int, model_id: str, enabled: bool
) -> None:
    row = (
        db.query(UserModelSetting)
        .filter(
            UserModelSetting.user_id == user_id,
            UserModelSetting.model_id == model_id,
        )
        .first()
    )
    if row:
        row.enabled = enabled
    else:
        db.add(
            UserModelSetting(
                user_id=user_id,
                model_id=model_id,
                enabled=enabled,
            )
        )


def get_admin_enabled_model_ids(db: Session) -> set[str]:
    admin_map = _admin_enabled_map(db)
    return {model_id for model_id, on in admin_map.items() if on}


def get_user_enabled_model_ids(db: Session, user_id: int) -> set[str]:
    user_map = _user_enabled_map(db, user_id)
    return {model_id for model_id, on in user_map.items() if on}


def get_enabled_model_ids(db: Session, user_id: int) -> set[str]:
    admin_map = _admin_enabled_map(db)
    user_map = _user_enabled_map(db, user_id)
    return {
        model_id
        for model_id in get_unique_routable_model_ids()
        if admin_map.get(model_id, True) and user_map.get(model_id, True)
    }


def is_model_enabled(db: Session, model_id: str, user_id: int) -> bool:
    return model_id in get_enabled_model_ids(db, user_id)


def is_admin_model_enabled(db: Session, model_id: str) -> bool:
    return _admin_enabled_map(db).get(model_id, True)


def explain_preferred_unavailable(
    preferred_id: str,
    db: Session,
    user_id: int,
) -> tuple[str, str]:
    admin_ok = is_admin_model_enabled(db, preferred_id)
    user_ok = preferred_id in get_user_enabled_model_ids(db, user_id)

    if not admin_ok and not user_ok:
        fragment = (
            f"Preferred model ({preferred_id}) is disabled by admin "
            f"and in your preferences."
        )
        badge = FALLBACK_BADGE_ADMIN
    elif not admin_ok:
        fragment = f"Preferred model ({preferred_id}) is disabled by admin."
        badge = FALLBACK_BADGE_ADMIN
    else:
        fragment = (
            f"Preferred model ({preferred_id}) is disabled in your preferences."
        )
        badge = FALLBACK_BADGE_USER

    return fragment, badge


def _best_tasks_for_model(model_id: str) -> list[str]:
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


def _base_model_row(record, admin_enabled: bool, user_enabled: bool) -> dict:
    model_id = record.model_id
    meta = record.metadata
    cost_in, cost_out = cost_per_1k_tokens(model_id, meta)
    disabled_by_admin = not admin_enabled
    effective = admin_enabled and user_enabled

    return {
        "model_id": model_id,
        "name": meta["model_name"],
        "provider": meta["provider"],
        "tier": tier_for_model(model_id, meta),
        "task_types": _best_tasks_for_model(model_id),
        "admin_enabled": admin_enabled,
        "user_enabled": user_enabled,
        "disabled_by_admin": disabled_by_admin,
        "available": effective,
        "enabled": effective,
        "cost_per_1k_input": cost_in,
        "cost_per_1k_output": cost_out,
    }


def list_model_settings(db: Session, user_id: int, *, is_admin: bool) -> list[dict]:
    """
    Unified Model Controls list for GET /model-settings.

    Always returns every routable model; empty settings tables default to enabled.
    """
    admin_map = _admin_enabled_map(db)
    user_map = _user_enabled_map(db, user_id)
    results: list[dict] = []
    for record in get_routable_models():
        model_id = record.model_id
        admin_enabled = admin_map.get(model_id, True)
        user_enabled = user_map.get(model_id, True)
        row = _base_model_row(record, admin_enabled, user_enabled)
        row["toggle_enabled"] = admin_enabled if is_admin else user_enabled
        results.append(row)
    return results


def save_model_settings(
    db: Session, user_id: int, updates: list[dict], *, is_admin: bool
) -> list[dict]:
    """Unified save for PUT /model-settings (admin vs user layer by role)."""
    if is_admin:
        save_admin_model_settings(db, updates)
    else:
        save_user_model_settings(db, user_id, updates)
    return list_model_settings(db, user_id, is_admin=is_admin)


def list_admin_model_settings(db: Session) -> list[dict]:
    """Admin Model Controls — org-wide toggles only."""
    admin_map = _admin_enabled_map(db)
    results: list[dict] = []
    for record in get_routable_models():
        admin_enabled = admin_map.get(record.model_id, True)
        row = _base_model_row(record, admin_enabled, user_enabled=True)
        row["enabled"] = admin_enabled
        row["toggle_enabled"] = admin_enabled
        results.append(row)
    return results


def list_user_model_settings(db: Session, user_id: int) -> list[dict]:
    """User Model Controls — personal toggles with admin lock state."""
    admin_map = _admin_enabled_map(db)
    user_map = _user_enabled_map(db, user_id)
    results: list[dict] = []
    for record in get_routable_models():
        model_id = record.model_id
        admin_enabled = admin_map.get(model_id, True)
        user_enabled = user_map.get(model_id, True)
        row = _base_model_row(record, admin_enabled, user_enabled)
        row["toggle_enabled"] = user_enabled
        results.append(row)
    return results


def save_admin_model_settings(db: Session, updates: list[dict]) -> list[dict]:
    """UPSERT admin_model_settings for every model in the payload."""
    known_ids = set(get_unique_routable_model_ids())

    for item in updates:
        model_id = item["model_id"]
        if model_id not in known_ids:
            continue
        _upsert_admin_setting(db, model_id, bool(item["enabled"]))

    db.commit()
    return list_admin_model_settings(db)  # internal helper; prefer list_model_settings


def save_user_model_settings(
    db: Session, user_id: int, updates: list[dict]
) -> list[dict]:
    """UPSERT user_model_settings; skip toggles on admin-disabled models."""
    known_ids = set(get_unique_routable_model_ids())
    admin_map = _admin_enabled_map(db)

    for item in updates:
        model_id = item["model_id"]
        if model_id not in known_ids:
            continue
        if not admin_map.get(model_id, True):
            continue
        _upsert_user_setting(db, user_id, model_id, bool(item["enabled"]))

    db.commit()
    return list_user_model_settings(db, user_id)


# Legacy combined helpers (used by old /settings/models routes if kept)
def list_model_controls(db: Session, user_id: int, *, is_admin: bool) -> list[dict]:
    if is_admin:
        return list_admin_model_settings(db)
    return list_user_model_settings(db, user_id)


def update_admin_model_controls(
    db: Session, updates: list[dict], *, admin_user_id: int
) -> list[dict]:
    return save_admin_model_settings(db, updates)


def update_user_model_controls(
    db: Session, user_id: int, updates: list[dict]
) -> list[dict]:
    return save_user_model_settings(db, user_id, updates)


update_model_controls = update_admin_model_controls


class NoModelsEnabledError(Exception):
    """Raised when routing cannot proceed because every model is disabled."""
