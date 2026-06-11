"""
Timezone utilities — UTC in the database, America/New_York in API responses.

Only call format_eastern_timestamp() when building JSON for the client.
Never call astimezone() on strings — parse with fromisoformat() first.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

EASTERN = ZoneInfo("America/New_York")


def format_eastern_timestamp(value: datetime | str | None) -> str | None:
    """
    Convert a UTC datetime (or ISO string) to Eastern display text.

    Example: 6/11/2026 9:28 AM EDT

    Returns None when value is missing or cannot be parsed.
    """
    if value is None:
        return None

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            value = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("Invalid timestamp string: %r", value)
            return None

    if not isinstance(value, datetime):
        logger.warning("Unsupported timestamp type: %s", type(value))
        return None

    try:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)

        local_time = value.astimezone(EASTERN)
        month = local_time.month
        day = local_time.day
        year = local_time.year
        hour = int(local_time.strftime("%I"))
        minute = local_time.strftime("%M")
        am_pm = local_time.strftime("%p")
        tz_label = local_time.tzname() or "ET"
        return f"{month}/{day}/{year} {hour}:{minute} {am_pm} {tz_label}"
    except (ValueError, OSError, OverflowError) as exc:
        logger.warning("Failed to format timestamp %r: %s", value, exc)
        return None


def format_timestamp_eastern(value: datetime | str | None) -> str:
    """API helper — never raises; returns empty string when formatting fails."""
    return format_eastern_timestamp(value) or ""
