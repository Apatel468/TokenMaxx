"""
Tests for activity logs — chat, documents, and secret redaction.
"""

from __future__ import annotations

import json
from io import BytesIO

from database import ActivityLog
from services.activity_log_service import sanitize_metadata
from tests.conftest import auth_headers


def test_chat_creates_activity_logs(client, auth_token, test_db):
    response = client.post(
        "/chat",
        json={"prompt": "Hello logs?", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200

    logs = (
        test_db.query(ActivityLog)
        .filter(ActivityLog.event_type == "chat_request_received")
        .all()
    )
    assert logs

    event_types = {row.event_type for row in test_db.query(ActivityLog).all()}
    assert "routing_completed" in event_types
    assert "model_call_completed" in event_types


def test_document_upload_creates_activity_logs(client, auth_token, test_db):
    upload = client.post(
        "/documents/upload",
        headers=auth_headers(auth_token),
        files={"file": ("notes.txt", BytesIO(b"Log test document."), "text/plain")},
    )
    assert upload.status_code == 200

    events = [row.event_type for row in test_db.query(ActivityLog).all()]
    assert "document_upload_started" in events
    assert "document_indexed" in events


def test_logs_never_include_raw_api_keys(client, auth_token, test_db):
    client.post(
        "/user/api-keys",
        json={"provider": "groq", "api_key": "gsk-super-secret-log-key", "key_label": "X"},
        headers=auth_headers(auth_token),
    )

    for row in test_db.query(ActivityLog).all():
        blob = (row.metadata_json or "") + row.message
        assert "gsk-super-secret-log-key" not in blob


def test_sanitize_metadata_redacts_secrets():
    meta = sanitize_metadata(
        {
            "api_key": "sk-live-secret",
            "model": "groq/llama",
            "password": "hunter2",
        }
    )
    assert meta["model"] == "groq/llama"
    assert "hunter2" not in json.dumps(meta)
    assert "sk-live-secret" not in json.dumps(meta)


def test_user_logs_endpoint(client, auth_token):
    client.post(
        "/chat",
        json={"prompt": "Fetch my logs", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )
    logs = client.get("/logs/my?limit=20", headers=auth_headers(auth_token))
    assert logs.status_code == 200
    body = logs.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert "event_type" in body[0]
    assert "metadata" in body[0]
