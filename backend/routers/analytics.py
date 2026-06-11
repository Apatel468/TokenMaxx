"""
Analytics router — SQLite stats from stored chat requests (Phase 3).

All endpoints are scoped to the logged-in user's own usage.
Admins use GET /admin/employee-usage for organization-wide metrics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import User, get_db
from models import AnalyticsSummary, HistoryRecord, ModelUsageRecord
from services.auth_dependencies import get_current_user
from services.report_generator import (
    generate_analytics_summary,
    get_history,
    get_model_usage,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsSummary:
    """Return total chats, costs, premium baseline, savings, and savings % for this user."""
    return generate_analytics_summary(db, current_user.id)


@router.get("/history", response_model=list[HistoryRecord])
def chat_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HistoryRecord]:
    """Return recent chat requests with prompt, response, and cost metrics."""
    return get_history(db, current_user.id, limit=limit)


@router.get("/model-usage", response_model=list[ModelUsageRecord])
def model_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ModelUsageRecord]:
    """Return how often each model was used and total cost per model."""
    return get_model_usage(db, current_user.id)
