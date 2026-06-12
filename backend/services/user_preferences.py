"""
User Preferences — per-account settings persisted in SQLite.

enhance_prompts: when False, POST /chat skips the prompt enhancement step.
Missing rows default to True (backward compatible).
"""

from sqlalchemy.orm import Session

from database import UserPreference

DEFAULT_ENHANCE_PROMPTS = True


def get_enhance_prompts(db: Session, user_id: int) -> bool:
    """Return whether prompt enhancement is enabled for this user."""
    row = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user_id)
        .first()
    )
    if row is None:
        return DEFAULT_ENHANCE_PROMPTS
    return bool(row.enhance_prompts)


def set_enhance_prompts(db: Session, user_id: int, enabled: bool) -> bool:
    """UPSERT enhance_prompts for a user."""
    row = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user_id)
        .first()
    )
    if row is None:
        row = UserPreference(user_id=user_id, enhance_prompts=enabled)
        db.add(row)
    else:
        row.enhance_prompts = enabled
    db.commit()
    db.refresh(row)
    return bool(row.enhance_prompts)
