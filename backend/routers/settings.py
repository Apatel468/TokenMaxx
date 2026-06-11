"""
Settings router — Model Controls API.

GET  /settings/models  → list routable models with enable/disable state
PUT  /settings/models  → update which models the router may use
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import ModelControlItem, ModelControlsUpdate
from services.model_settings import list_model_controls, update_model_controls

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/models", response_model=list[ModelControlItem])
def get_model_controls(db: Session = Depends(get_db)) -> list[ModelControlItem]:
    """Return all routable models and their enabled state for Model Controls."""
    return [ModelControlItem(**row) for row in list_model_controls(db)]


@router.put("/models", response_model=list[ModelControlItem])
def put_model_controls(
    body: ModelControlsUpdate,
    db: Session = Depends(get_db),
) -> list[ModelControlItem]:
    """Save enable/disable toggles from the Model Controls UI."""
    updates = [item.model_dump() for item in body.models]
    rows = update_model_controls(db, updates)
    return [ModelControlItem(**row) for row in rows]
