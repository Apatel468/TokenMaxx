"""
Settings router — legacy /settings/models aliases redirect logic to /model-settings.

Prefer GET/PUT /model-settings for Model Controls.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import User, get_db
from models import ModelControlItem, ModelControlsUpdate
from services.auth_dependencies import get_current_user
from services.model_settings import list_model_settings, save_model_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/models", response_model=list[ModelControlItem])
def get_model_controls_legacy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ModelControlItem]:
    """Legacy alias for GET /model-settings."""
    is_admin = current_user.role == "admin"
    rows = list_model_settings(db, current_user.id, is_admin=is_admin)
    return [ModelControlItem(**row) for row in rows]


@router.put("/models", response_model=list[ModelControlItem])
def put_model_controls_legacy(
    body: ModelControlsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ModelControlItem]:
    """Legacy alias for PUT /model-settings."""
    is_admin = current_user.role == "admin"
    updates = [item.model_dump() for item in body.models]
    rows = save_model_settings(db, current_user.id, updates, is_admin=is_admin)
    return [ModelControlItem(**row) for row in rows]
