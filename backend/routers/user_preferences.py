"""
User preferences router — GET/PUT /user/preferences.

Per-user settings such as prompt enhancement toggle.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import User, get_db
from models import UserPreferencesOut, UserPreferencesUpdate
from services.auth_dependencies import get_current_user
from services.user_preferences import get_enhance_prompts, set_enhance_prompts

router = APIRouter(prefix="/user", tags=["user-preferences"])


@router.get("/preferences", response_model=UserPreferencesOut)
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserPreferencesOut:
    """Return saved preferences for the logged-in user."""
    return UserPreferencesOut(
        enhance_prompts=get_enhance_prompts(db, current_user.id),
    )


@router.put("/preferences", response_model=UserPreferencesOut)
def update_preferences(
    body: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserPreferencesOut:
    """Save user preferences (e.g. prompt enhancement toggle)."""
    enabled = set_enhance_prompts(db, current_user.id, body.enhance_prompts)
    return UserPreferencesOut(enhance_prompts=enabled)
