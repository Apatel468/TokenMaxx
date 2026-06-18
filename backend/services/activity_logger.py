"""
Activity log persistence with safe metadata redaction.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from database import ActivityLog
from services.key_encryption import redact_sensitive_value

LOG_LEVELS = ("info", "warning", "error")

_SENSITIVE_METADATA_KEYS = {
    "api_key",
    "encrypted_api_key",
    "password",
    "access_token",
    "refresh_token",
    "token",
    "authorization",
    "jwt",
    "jwt_token",
    "bearer_token",
    "raw_prompt",
    "document_text",
    "document_content",
    "full_document",
    "chunk_text",
    "chunk_content",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_request_id() -> str:
    """Correlation id for all activity logs in one chat/regenerate request."""
    return str(uuid.uuid4())


def with_request_meta(
    metadata: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Merge request correlation fields into log metadata."""
    meta = dict(metadata or {})
    if request_id:
        meta["request_id"] = request_id
    meta.update(extra)
    return meta


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Remove or mask secrets and large raw content from log metadata."""
    if not metadata:
        return {}

    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        lower = key.lower()
        if lower in _SENSITIVE_METADATA_KEYS:
            continue
        if any(part in lower for part in ("password", "token", "secret", "api_key")):
            safe[key] = redact_sensitive_value(key, value)
            continue
        if isinstance(value, str) and len(value) > 2000:
            safe[key] = value[:2000] + "…[truncated]"
            continue
        if isinstance(value, dict):
            safe[key] = sanitize_metadata(value)
            continue
        if isinstance(value, list) and value and isinstance(value[0], str):
            if sum(len(item) for item in value) > 4000:
                safe[key] = [f"{len(value)} items"]
                continue
        safe[key] = value
    return safe


def record_activity(
    db: Session,
    *,
    user_id: int,
    level: str = "info",
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
    conversation_id: int | None = None,
    message_id: int | None = None,
) -> ActivityLog:
    """Persist one activity log row (caller commits)."""
    level = level if level in LOG_LEVELS else "info"
    safe_meta = sanitize_metadata(metadata)
    entry = ActivityLog(
        user_id=user_id,
        conversation_id=conversation_id,
        message_id=message_id,
        level=level,
        event_type=event_type,
        message=message,
        metadata_json=json.dumps(safe_meta) if safe_meta else None,
        created_at=_utcnow(),
    )
    db.add(entry)
    db.flush()
    return entry


def parse_metadata_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


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


def fetch_activity_logs(
    db: Session,
    *,
    user_id: int | None = None,
    conversation_id: int | None = None,
    event_type: str | None = None,
    level: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
) -> list[ActivityLog]:
    """Query activity logs with optional filters."""
    query = db.query(ActivityLog)
    if user_id is not None:
        query = query.filter(ActivityLog.user_id == user_id)
    if conversation_id is not None:
        query = query.filter(ActivityLog.conversation_id == conversation_id)
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
        return rows[:limit]

    filtered: list[ActivityLog] = []
    for row in rows:
        meta = parse_metadata_json(row.metadata_json)
        if provider and meta.get("provider") != provider:
            continue
        if model and meta.get("model") != model:
            continue
        filtered.append(row)
    return filtered[:limit]
