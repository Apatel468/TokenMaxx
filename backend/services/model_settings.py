"""
Model Settings — admin (org-wide) and per-user enable/disable preferences.

Effective routing availability:
    model_enabled = provider_enabled AND admin_enabled AND user_enabled

Missing DB rows default to enabled=True. Existing rows with enabled=False
are never overridden on load.
"""

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from config.model_registry import (
    CHAT_MODEL_IDS,
    ProviderName,
    cost_per_1k_tokens,
    get_provider_for_model,
    tier_for_model,
)
from database import AdminModelSetting, ProviderSetting, UserModelSetting
from services.config_loader import get_allowed_task_types, resolve_task_key
from services.groq_models import get_routable_model_ids, get_routable_models
from services.model_scorer import score_candidates

FALLBACK_BADGE_ADMIN = "Preferred model disabled by admin — fallback used"
FALLBACK_BADGE_USER = (
    "Preferred model disabled in your preferences — fallback used"
)
FALLBACK_BADGE = FALLBACK_BADGE_ADMIN

PROVIDER_DISPLAY_ORDER: tuple[ProviderName, ...] = (
    "groq",
    "anthropic",
    "openai",
    "google",
)


def get_catalog_providers() -> list[str]:
    """Unique providers from the routable chat catalog, in display order."""
    seen = {record.provider for record in get_routable_models()}
    return [provider for provider in PROVIDER_DISPLAY_ORDER if provider in seen]


def seed_provider_settings(db: Session) -> None:
    """Insert provider rows only when missing (default enabled)."""
    for provider in get_catalog_providers():
        existing = (
            db.query(ProviderSetting)
            .filter(ProviderSetting.provider_name == provider)
            .first()
        )
        if not existing:
            db.add(ProviderSetting(provider_name=provider, enabled=True))
    db.commit()


def _provider_enabled_map(db: Session) -> dict[str, bool]:
    """Read provider flags from DB; default True when row is missing."""
    seed_provider_settings(db)
    rows = {
        row.provider_name: row.enabled
        for row in db.query(ProviderSetting).all()
    }
    return {
        provider: bool(rows[provider]) if provider in rows else True
        for provider in get_catalog_providers()
    }


def is_provider_enabled(db: Session, provider: str) -> bool:
    return _provider_enabled_map(db).get(provider, True)


def get_enabled_provider_names(db: Session) -> set[str]:
    provider_map = _provider_enabled_map(db)
    return {name for name, on in provider_map.items() if on}


def list_provider_settings(db: Session) -> list[dict]:
    """Provider toggles with model counts for Model Controls."""
    provider_map = _provider_enabled_map(db)
    counts: dict[str, int] = {provider: 0 for provider in get_catalog_providers()}
    for record in get_routable_models():
        counts[record.provider] = counts.get(record.provider, 0) + 1

    return [
        {
            "provider": provider,
            "enabled": provider_map.get(provider, True),
            "model_count": counts.get(provider, 0),
        }
        for provider in get_catalog_providers()
    ]


def save_provider_settings(db: Session, updates: list[dict]) -> list[dict]:
    """UPSERT provider_settings for known catalog providers."""
    known = set(get_catalog_providers())
    for item in updates:
        provider = item["provider"]
        if provider not in known:
            continue
        row = (
            db.query(ProviderSetting)
            .filter(ProviderSetting.provider_name == provider)
            .first()
        )
        if row:
            row.enabled = bool(item["enabled"])
        else:
            db.add(
                ProviderSetting(
                    provider_name=provider,
                    enabled=bool(item["enabled"]),
                )
            )
    db.commit()
    return list_provider_settings(db)


def get_unique_routable_model_ids() -> list[str]:
    return get_routable_model_ids()


def cleanup_stale_model_settings(db: Session) -> int:
    """
    Remove admin/user settings rows for models no longer in the chat allowlist.

    Historical model_runs with old model ids are untouched for analytics.
    """
    allowed = set(CHAT_MODEL_IDS)
    removed = 0
    for row in db.query(AdminModelSetting).all():
        if row.model_id not in allowed:
            db.delete(row)
            removed += 1
    for row in db.query(UserModelSetting).all():
        if row.model_id not in allowed:
            db.delete(row)
            removed += 1
    if removed:
        db.commit()
        logger.info("Removed %d stale model_settings rows (outside allowlist).", removed)
    return removed


def seed_admin_model_settings(db: Session) -> None:
    """Insert admin rows only for models that have no row yet (default enabled)."""
    cleanup_stale_model_settings(db)
    for model_id in get_unique_routable_model_ids():
        existing = (
            db.query(AdminModelSetting)
            .filter(AdminModelSetting.model_id == model_id)
            .first()
        )
        if not existing:
            db.add(AdminModelSetting(model_id=model_id, enabled=True))
    db.commit()


def seed_user_model_settings(db: Session, user_id: int) -> None:
    """
    Insert user rows for routable catalog models that have no preference yet.

    Defaults to enabled=True. Does not change existing rows.
    """
    routable_ids = set(get_unique_routable_model_ids())
    existing_ids = {
        row.model_id
        for row in db.query(UserModelSetting)
        .filter(UserModelSetting.user_id == user_id)
        .all()
    }
    added = False
    for model_id in routable_ids:
        if model_id not in existing_ids:
            db.add(
                UserModelSetting(
                    user_id=user_id,
                    model_id=model_id,
                    enabled=True,
                    explicitly_set=False,
                )
            )
            added = True
    if added:
        db.commit()


def sync_user_model_settings(db: Session, user_id: int) -> None:
    """
    Align user model preferences with the routable catalog.

    - Drop stale rows outside the chat allowlist (e.g. whisper-large-v3)
    - Remove implicit disabled rows (enabled=False, never saved by the user)
    - Backfill missing routable models as enabled=True
    - Preserve rows the user explicitly saved via Model Controls
    """
    cleanup_stale_model_settings(db)
    routable_ids = set(get_unique_routable_model_ids())

    implicit_disabled = (
        db.query(UserModelSetting)
        .filter(
            UserModelSetting.user_id == user_id,
            UserModelSetting.enabled.is_(False),
            UserModelSetting.explicitly_set.is_(False),
        )
        .all()
    )
    removed = False
    for row in implicit_disabled:
        if row.model_id in routable_ids:
            db.delete(row)
            removed = True
    if removed:
        db.commit()

    seed_user_model_settings(db, user_id)


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
    sync_user_model_settings(db, user_id)
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
    db: Session,
    user_id: int,
    model_id: str,
    enabled: bool,
    *,
    explicitly_set: bool = True,
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
        row.explicitly_set = explicitly_set
    else:
        db.add(
            UserModelSetting(
                user_id=user_id,
                model_id=model_id,
                enabled=enabled,
                explicitly_set=explicitly_set,
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
    provider_map = _provider_enabled_map(db)
    return {
        model_id
        for model_id in get_unique_routable_model_ids()
        if admin_map.get(model_id, True)
        and user_map.get(model_id, True)
        and provider_map.get(get_provider_for_model(model_id), True)
    }


def is_model_enabled(db: Session, model_id: str, user_id: int) -> bool:
    return model_id in get_enabled_model_ids(db, user_id)


def get_model_disabled_reason(
    db: Session, user_id: int, model_id: str
) -> str | None:
    """
    Return a user-facing reason when a model cannot be selected, else None.

    Messages match the regenerate UI spec.
    """
    provider = get_provider_for_model(model_id)
    if not is_provider_enabled(db, provider):
        return "Disabled by administrator"
    admin_ok = is_admin_model_enabled(db, model_id)
    user_ok = model_id in get_user_enabled_model_ids(db, user_id)
    if admin_ok and user_ok:
        return None
    if not admin_ok:
        return "Disabled by administrator"
    return "Disabled in your preferences"


def is_admin_model_enabled(db: Session, model_id: str) -> bool:
    return _admin_enabled_map(db).get(model_id, True)


def explain_preferred_unavailable(
    preferred_id: str,
    db: Session,
    user_id: int,
) -> tuple[str, str]:
    provider = get_provider_for_model(preferred_id)
    if not is_provider_enabled(db, provider):
        fragment = f"Preferred model ({preferred_id}) is disabled — provider {provider} is off."
        return fragment, FALLBACK_BADGE_ADMIN

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


def _base_model_row(
    record,
    admin_enabled: bool,
    user_enabled: bool,
    *,
    provider_enabled: bool = True,
) -> dict:
    model_id = record.model_id
    meta = record.metadata
    cost_in, cost_out = cost_per_1k_tokens(model_id, meta)
    disabled_by_provider = not provider_enabled
    disabled_by_admin = not admin_enabled
    effective = provider_enabled and admin_enabled and user_enabled

    return {
        "model_id": model_id,
        "name": meta["model_name"],
        "provider": meta["provider"],
        "tier": tier_for_model(model_id, meta),
        "task_types": _best_tasks_for_model(model_id),
        "provider_enabled": provider_enabled,
        "admin_enabled": admin_enabled,
        "user_enabled": user_enabled,
        "disabled_by_provider": disabled_by_provider,
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
    provider_map = _provider_enabled_map(db)
    results: list[dict] = []
    for record in get_routable_models():
        model_id = record.model_id
        admin_enabled = admin_map.get(model_id, True)
        user_enabled = user_map.get(model_id, True)
        provider_enabled = provider_map.get(record.provider, True)
        row = _base_model_row(
            record,
            admin_enabled,
            user_enabled,
            provider_enabled=provider_enabled,
        )
        row["toggle_enabled"] = (
            provider_enabled and admin_enabled
            if is_admin
            else provider_enabled and user_enabled and admin_enabled
        )
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
    provider_map = _provider_enabled_map(db)
    results: list[dict] = []
    for record in get_routable_models():
        admin_enabled = admin_map.get(record.model_id, True)
        provider_enabled = provider_map.get(record.provider, True)
        row = _base_model_row(
            record,
            admin_enabled,
            user_enabled=True,
            provider_enabled=provider_enabled,
        )
        row["enabled"] = provider_enabled and admin_enabled
        row["toggle_enabled"] = provider_enabled and admin_enabled
        results.append(row)
    return results


def list_user_model_settings(db: Session, user_id: int) -> list[dict]:
    """User Model Controls — personal toggles with admin lock state."""
    admin_map = _admin_enabled_map(db)
    user_map = _user_enabled_map(db, user_id)
    provider_map = _provider_enabled_map(db)
    results: list[dict] = []
    for record in get_routable_models():
        model_id = record.model_id
        admin_enabled = admin_map.get(model_id, True)
        user_enabled = user_map.get(model_id, True)
        provider_enabled = provider_map.get(record.provider, True)
        row = _base_model_row(
            record,
            admin_enabled,
            user_enabled,
            provider_enabled=provider_enabled,
        )
        row["toggle_enabled"] = provider_enabled and user_enabled and admin_enabled
        results.append(row)
    return results


def save_admin_model_settings(db: Session, updates: list[dict]) -> list[dict]:
    """UPSERT admin_model_settings for every model in the payload."""
    known_ids = set(get_unique_routable_model_ids())
    provider_map = _provider_enabled_map(db)

    for item in updates:
        model_id = item["model_id"]
        if model_id not in known_ids:
            continue
        if not provider_map.get(get_provider_for_model(model_id), True):
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
    provider_map = _provider_enabled_map(db)

    for item in updates:
        model_id = item["model_id"]
        if model_id not in known_ids:
            continue
        if not provider_map.get(get_provider_for_model(model_id), True):
            continue
        if not admin_map.get(model_id, True):
            continue
        _upsert_user_setting(
            db, user_id, model_id, bool(item["enabled"]), explicitly_set=True
        )

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
