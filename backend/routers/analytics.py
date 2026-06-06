"""
Analytics router — SQLite stats from stored chat requests (Phase 3).

GET /analytics/summary     → totals: chats, cost, savings
GET /analytics/history     → recent prompt/response rows
GET /analytics/model-usage → breakdown by Groq model
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import AnalyticsSummary, HistoryRecord, ModelUsageRecord
from services.report_generator import (
    generate_analytics_summary,
    get_history,
    get_model_usage,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(db: Session = Depends(get_db)) -> AnalyticsSummary:
    """Return total chats, costs, premium baseline, savings, and savings %."""
    return generate_analytics_summary(db)


@router.get("/history", response_model=list[HistoryRecord])
def chat_history(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[HistoryRecord]:
    """Return recent chat requests with prompt, response, and cost metrics."""
    return get_history(db, limit=limit)


@router.get("/model-usage", response_model=list[ModelUsageRecord])
def model_usage(db: Session = Depends(get_db)) -> list[ModelUsageRecord]:
    """Return how often each model was used and total cost per model."""
    return get_model_usage(db)
