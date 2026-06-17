"""
Activity logs router — user and conversation log views.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import ActivityLog, User, get_db
from models import ActivityLogOut
from services.activity_logger import fetch_activity_logs, parse_metadata_json
from services.auth_dependencies import get_current_user
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
    rows = fetch_activity_logs(
        db,
        user_id=current_user.id,
        event_type=event_type,
        level=level,
        provider=provider,
        model=model,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return [_to_log_out(row) for row in rows]


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
    rows = fetch_activity_logs(
        db,
        user_id=current_user.id,
        conversation_id=conversation_id,
        event_type=event_type,
        level=level,
        provider=provider,
        model=model,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return [_to_log_out(row) for row in rows]
