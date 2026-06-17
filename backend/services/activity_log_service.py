"""
Activity log persistence with safe metadata redaction.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from database import ActivityLog
from services.key_encryption import redact_sensitive_value

LOG_LEVELS = ("info", "warning", "error")

_SENSITIVE_METADATA_KEYS = {
    "api_key",
    "encrypted_api_key",
    "password",
    "access_token",
    "token",
    "authorization",
    "jwt",
    "raw_prompt",
    "document_text",
    "chunk_text",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
