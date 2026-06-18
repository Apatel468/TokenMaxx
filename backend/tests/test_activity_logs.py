"""
Tests for activity logs — chat, documents, access control, and secret redaction.
"""

from __future__ import annotations

import json
from io import BytesIO

from database import ActivityLog, User
from services.activity_logger import record_activity, sanitize_metadata
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
    assert "rag_search_started" in event_types


def test_chat_logs_share_request_id(client, auth_token, test_db):
    client.post(
        "/chat",
        json={"prompt": "Grouped logs test", "enhance_prompt": True},
        headers=auth_headers(auth_token),
    )
    rows = test_db.query(ActivityLog).all()
    pipeline = [
        row for row in rows
        if row.event_type in {
            "chat_request_received",
            "prompt_enhancement_started",
            "routing_completed",
            "model_call_completed",
        }
    ]
    request_ids = {
        json.loads(row.metadata_json or "{}").get("request_id")
        for row in pipeline
    }
    request_ids.discard(None)
    assert len(request_ids) == 1


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
            "jwt_token": "eyJhbGciOiJIUzI1NiJ9.secret",
            "document_content": "Full confidential document body.",
        }
    )
    assert meta["model"] == "groq/llama"
    serialized = json.dumps(meta)
    assert "hunter2" not in serialized
    assert "sk-live-secret" not in serialized
    assert "eyJhbGciOiJIUzI1NiJ9" not in serialized
    assert "confidential document" not in serialized


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


def test_user_cannot_view_another_users_logs(client, auth_token, test_db):
    other = client.post(
        "/auth/signup",
        json={"email": "other-user@example.com", "password": "testpass123"},
    )
    assert other.status_code == 200
    other_token = other.json()["access_token"]

    client.post(
        "/chat",
        json={"prompt": "Other user chat", "enhance_prompt": False},
        headers=auth_headers(other_token),
    )

    my_logs = client.get("/logs/my?limit=50", headers=auth_headers(auth_token))
    assert my_logs.status_code == 200
    other_user_id = test_db.query(User).filter(User.email == "other-user@example.com").one().id
    assert all(row["user_id"] != other_user_id for row in my_logs.json())


def test_admin_can_view_all_logs(client, auth_token, test_db):
    admin_user = test_db.query(User).filter(User.email == "pytest-user@example.com").one()
    admin_user.role = "admin"
    test_db.commit()

    other = client.post(
        "/auth/signup",
        json={"email": "logged-user@example.com", "password": "testpass123"},
    )
    other_token = other.json()["access_token"]
    client.post(
        "/chat",
        json={"prompt": "Admin should see this", "enhance_prompt": False},
        headers=auth_headers(other_token),
    )

    admin_logs = client.get("/admin/logs?limit=50", headers=auth_headers(auth_token))
    assert admin_logs.status_code == 200
    body = admin_logs.json()
    assert isinstance(body, list)
    user_ids = {row["user_id"] for row in body}
    other_user_id = test_db.query(User).filter(User.email == "logged-user@example.com").one().id
    assert other_user_id in user_ids


def test_non_admin_cannot_access_admin_logs(client, auth_token):
    response = client.get("/admin/logs", headers=auth_headers(auth_token))
    assert response.status_code == 403


def test_record_activity_strips_document_text_from_metadata(test_db):
    user = test_db.query(User).first()
    if user is None:
        user = User(email="log-user@example.com", hashed_password="x", role="user")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

    record_activity(
        test_db,
        user_id=user.id,
        event_type="document_indexed",
        message="Indexed document.",
        metadata={
            "filename": "secret.txt",
            "document_content": "This is the full secret document text.",
            "chunk_text": "chunk one secret content",
        },
    )
    test_db.commit()

    row = test_db.query(ActivityLog).order_by(ActivityLog.id.desc()).first()
    assert row is not None
    meta = json.loads(row.metadata_json or "{}")
    assert meta.get("filename") == "secret.txt"
    assert "document_content" not in meta
    assert "chunk_text" not in meta
    assert "secret document" not in (row.metadata_json or "")
