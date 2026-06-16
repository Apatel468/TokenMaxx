"""Server-Sent Events formatting helpers."""

from __future__ import annotations

import json
from typing import Any


def format_sse(event: str, data: Any) -> str:
    """Format one SSE message block."""
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"
