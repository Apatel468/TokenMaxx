"""
Model settings router — unified GET/PUT /model-settings.

Returns every routable model with admin_enabled, user_enabled, and available.
Never returns 404 when settings tables are empty (defaults to enabled).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import User, get_db
from models import ModelControlItem, ModelControlsUpdate
from services.auth_dependencies import get_current_user
from services.model_settings import list_model_settings, save_model_settings

router = APIRouter(prefix="/model-settings", tags=["model-settings"])


@router.get("", response_model=list[ModelControlItem])
def get_model_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ModelControlItem]:
    """
    All routable models with preference overlay for the current user.

    Missing DB rows default to enabled=True.
    """
    is_admin = current_user.role == "admin"
    rows = list_model_settings(db, current_user.id, is_admin=is_admin)
    return [ModelControlItem(**row) for row in rows]


@router.put("", response_model=list[ModelControlItem])
def put_model_settings(
    body: ModelControlsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ModelControlItem]:
    """
    UPSERT model preferences.

    Admins update organization-wide (admin_enabled); users update personal (user_enabled).
    """
    is_admin = current_user.role == "admin"
    updates = [item.model_dump() for item in body.models]
    rows = save_model_settings(db, current_user.id, updates, is_admin=is_admin)
    return [ModelControlItem(**row) for row in rows]
