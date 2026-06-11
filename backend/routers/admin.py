"""
Admin router — employee usage metrics and org-wide model settings.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import EmployeeUsageRecord
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
