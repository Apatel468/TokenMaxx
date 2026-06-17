"""
Admin router — employee usage metrics, org-wide model settings, and activity logs.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import ActivityLog, User, get_db
from models import ActivityLogOut, EmployeeUsageRecord
from routers.logs import _to_log_out
from services.activity_logger import fetch_activity_logs
from services.auth_dependencies import require_admin
from services.report_generator import get_employee_usage_metrics

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/employee-usage", response_model=list[EmployeeUsageRecord])
def employee_usage(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> list[EmployeeUsageRecord]:
    """Per-user chat cost and model breakdown (admin only)."""
    return get_employee_usage_metrics(db)


@router.get("/logs", response_model=list[ActivityLogOut])
def get_admin_logs(
    limit: int = Query(200, ge=1, le=1000),
    user_id: int | None = None,
    event_type: str | None = None,
    level: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> list[ActivityLogOut]:
    """All activity logs across users (admin only)."""
    _ = admin
    rows = fetch_activity_logs(
        db,
        user_id=user_id,
        event_type=event_type,
        level=level,
        provider=provider,
        model=model,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    email_by_id = {u.id: u.email for u in db.query(User).all()}
    return [
        _to_log_out(row, email_by_id.get(row.user_id)) for row in rows
    ]
