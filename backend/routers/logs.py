"""
Activity logs router — user, conversation, and admin log views.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import ActivityLog, User, get_db
from models import ActivityLogOut
from services.activity_log_service import parse_metadata_json
from services.auth_dependencies import get_current_user, require_admin
from services.conversation_store import get_conversation_or_404
from services.timezone_utils import format_timestamp_eastern

router = APIRouter(prefix="/logs", tags=["logs"])


def _format_created_at(dt) -> str:
    return format_timestamp_eastern(dt)


def _to_log_out(row: ActivityLog, user_email: str | None = None) -> ActivityLogOut:
    return ActivityLogOut(
        id=row.id,
        user_id=row.user_id,
        conversation_id=row.conversation_id,
        message_id=row.message_id,
        level=row.level,
        event_type=row.event_type,
        message=row.message,
        metadata=parse_metadata_json(row.metadata_json),
        created_at=_format_created_at(row.created_at),
        user_email=user_email,
    )


def _parse_date(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    try:
        if "T" in value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if end_of_day:
                parsed = parsed.replace(hour=23, minute=59, second=59)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {value}",
        ) from exc


def _apply_log_filters(
    query,
    *,
    event_type: str | None,
    level: str | None,
    provider: str | None,
    model: str | None,
    start_date: str | None,
    end_date: str | None,
) -> list[ActivityLog]:
    if event_type:
        query = query.filter(ActivityLog.event_type == event_type)
    if level:
        query = query.filter(ActivityLog.level == level)
    start = _parse_date(start_date)
    end = _parse_date(end_date, end_of_day=True)
    if start:
        query = query.filter(ActivityLog.created_at >= start)
    if end:
        query = query.filter(ActivityLog.created_at <= end)

    rows = query.order_by(ActivityLog.created_at.desc()).all()
    if not provider and not model:
        return rows

    filtered: list[ActivityLog] = []
    for row in rows:
        meta = parse_metadata_json(row.metadata_json)
        if provider and meta.get("provider") != provider:
            continue
        if model and meta.get("model") != model:
            continue
        filtered.append(row)
    return filtered


@router.get("/my", response_model=list[ActivityLogOut])
def get_my_logs(
    limit: int = Query(100, ge=1, le=500),
    event_type: str | None = None,
    level: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ActivityLogOut]:
    query = db.query(ActivityLog).filter(ActivityLog.user_id == current_user.id)
    rows = _apply_log_filters(
        query,
        event_type=event_type,
        level=level,
        provider=provider,
        model=model,
        start_date=start_date,
        end_date=end_date,
    )
    return [_to_log_out(row) for row in rows[:limit]]


@router.get("/conversation/{conversation_id}", response_model=list[ActivityLogOut])
def get_conversation_logs(
    conversation_id: int,
    limit: int = Query(100, ge=1, le=500),
    event_type: str | None = None,
    level: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ActivityLogOut]:
    get_conversation_or_404(db, conversation_id, user=current_user)
    query = db.query(ActivityLog).filter(
        ActivityLog.user_id == current_user.id,
        ActivityLog.conversation_id == conversation_id,
    )
    rows = _apply_log_filters(
        query,
        event_type=event_type,
        level=level,
        provider=provider,
        model=model,
        start_date=start_date,
        end_date=end_date,
    )
    return [_to_log_out(row) for row in rows[:limit]]


@router.get("/admin/logs", response_model=list[ActivityLogOut])
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
    _ = admin
    query = db.query(ActivityLog)
    if user_id is not None:
        query = query.filter(ActivityLog.user_id == user_id)
    rows = _apply_log_filters(
        query,
        event_type=event_type,
        level=level,
        provider=provider,
        model=model,
        start_date=start_date,
        end_date=end_date,
    )
    email_by_id = {u.id: u.email for u in db.query(User).all()}
    return [
        _to_log_out(row, email_by_id.get(row.user_id)) for row in rows[:limit]
    ]
