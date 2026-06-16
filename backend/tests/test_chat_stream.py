"""
Tests for POST /chat/stream SSE endpoint.

LLM streaming is mocked in conftest — no Groq calls.
"""

from __future__ import annotations

import json

from tests.conftest import auth_headers


def _parse_sse_events(raw: str) -> list[tuple[str, dict]]:
    """Parse SSE payload into (event_name, data_dict) pairs."""
    events: list[tuple[str, dict]] = []
    for block in raw.split("\n\n"):
        if not block.strip():
            continue
        event_type = "message"
        data = ""
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data += line[5:].strip()
        if data:
            events.append((event_type, json.loads(data)))
    return events


def test_chat_stream_requires_authentication(client):
    response = client.post("/chat/stream", json={"prompt": "Hello?"})

    assert response.status_code == 401


def test_chat_stream_returns_sse_token_and_complete_events(client, auth_token):
    with client.stream(
        "POST",
        "/chat/stream",
        json={"prompt": "What is 2 + 2?", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        body = response.read().decode("utf-8")

    events = _parse_sse_events(body)
    event_names = [name for name, _ in events]

    assert "routing_start" in event_names
    assert "routing_complete" in event_names
    assert "token" in event_names
    assert "complete" in event_names

    tokens = [data["content"] for name, data in events if name == "token"]
    assert tokens
    assert "".join(tokens) == "Mocked LLM response for testing."

    complete = next(data for name, data in events if name == "complete")
    assert complete["mock_response"] == "Mocked LLM response for testing."
    assert complete["conversation_id"] > 0
    assert complete["assistant_message_id"] > 0
    assert complete["selected_model_id"]
    assert complete["task_type"]

    routing = next(data for name, data in events if name == "routing_complete")
    assert routing["selected_model_id"]
    assert routing["task_type"]


def test_non_streaming_chat_still_works(client, auth_token):
    response = client.post(
        "/chat",
        json={"prompt": "Still works?", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )

    assert response.status_code == 200
    assert response.json()["mock_response"] == "Mocked LLM response for testing."
