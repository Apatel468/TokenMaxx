"""
Tests for GET /admin/user-metrics — admin-only per-user usage aggregates.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from database import Conversation, Message, ModelRun, User
from services.admin_user_metrics import compute_session_stats, get_admin_user_metrics
from tests.conftest import auth_headers


def _make_admin(test_db, email: str = "pytest-user@example.com") -> User:
    user = test_db.query(User).filter(User.email == email).one()
    user.role = "admin"
    test_db.commit()
    return user


def test_admin_user_metrics_requires_admin(client, auth_token):
    response = client.get("/admin/user-metrics", headers=auth_headers(auth_token))
    assert response.status_code == 403


def test_admin_user_metrics_success(client, auth_token, test_db):
    _make_admin(test_db)
    client.post(
        "/chat",
        json={"prompt": "Admin metrics hello", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )

    response = client.get("/admin/user-metrics", headers=auth_headers(auth_token))
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 1

    row = next(item for item in body if item["email"] == "pytest-user@example.com")
    assert row["total_prompts"] >= 1
    assert row["role"] == "admin"
    assert "most_used_models" in row
    assert "feature_usage" in row
    assert "query_categories" in row
    assert "prompts_over_time" in row
    assert row["total_tokens"] >= 0
    assert "total_actual_cost" in row


def test_admin_user_metrics_user_filter(client, auth_token, test_db):
    _make_admin(test_db)

    other = client.post(
        "/auth/signup",
        json={"email": "metrics-other@example.com", "password": "testpass123"},
    )
    other_token = other.json()["access_token"]
    client.post(
        "/chat",
        json={"prompt": "Other user prompt", "enhance_prompt": False},
        headers=auth_headers(other_token),
    )
    client.post(
        "/chat",
        json={"prompt": "Admin user prompt", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )

    other_user = test_db.query(User).filter(User.email == "metrics-other@example.com").one()
    response = client.get(
        f"/admin/user-metrics?user_id={other_user.id}",
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["email"] == "metrics-other@example.com"
    assert body[0]["total_prompts"] >= 1


def test_session_grouping_30_minute_gap():
    base = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    timestamps = [
        base,
        base + timedelta(minutes=10),
        base + timedelta(minutes=20),
        base + timedelta(minutes=60),
        base + timedelta(minutes=70),
    ]
    session_count, avg = compute_session_stats(timestamps)
    assert session_count == 2
    assert avg == 2.5


def test_model_usage_and_category_aggregation(test_db):
    user = User(email="metrics-unit@example.com", hashed_password="x", role="user")
    test_db.add(user)
    test_db.flush()

    conv = Conversation(user_id=user.id, title="Test")
    test_db.add(conv)
    test_db.flush()

    msg = Message(conversation_id=conv.id, role="user", content="coding help")
    test_db.add(msg)
    test_db.flush()

    now = datetime.now(timezone.utc)
    runs = [
        ModelRun(
            conversation_id=conv.id,
            user_id=user.id,
            assistant_message_id=None,
            task_type="coding",
            selected_model="qwen/qwen3-32b",
            reason_selected="test",
            input_tokens=10,
            output_tokens=20,
            estimated_cost=0.001,
            premium_model_cost=0.01,
            savings_usd=0.009,
            savings_percentage=90.0,
            latency_ms=120.0,
            enhancement_enabled=True,
            rag_used=True,
            created_at=now,
        ),
        ModelRun(
            conversation_id=conv.id,
            user_id=user.id,
            assistant_message_id=None,
            task_type="general_qa",
            selected_model="llama-3.1-8b-instant",
            reason_selected="test",
            input_tokens=5,
            output_tokens=5,
            estimated_cost=0.0005,
            premium_model_cost=0.005,
            savings_usd=0.0045,
            savings_percentage=90.0,
            latency_ms=80.0,
            is_regeneration=True,
            created_at=now + timedelta(minutes=1),
        ),
    ]
    test_db.add_all(runs)
    test_db.commit()

    metrics = get_admin_user_metrics(test_db, user_id=user.id, granularity="daily")
    assert len(metrics) == 1
    row = metrics[0]
    assert row.total_prompts == 1
    assert row.most_used_models[0].model == "qwen/qwen3-32b"
    assert any(item.category == "coding" for item in row.query_categories)
    latency_by_model = {item.model: item.average_latency_ms for item in row.average_latency_by_model}
    assert latency_by_model["qwen/qwen3-32b"] == 120.0
    assert latency_by_model["llama-3.1-8b-instant"] == 80.0
    assert row.total_tokens == 40


def test_date_filter_excludes_old_runs(test_db):
    user = User(email="dated-user@example.com", hashed_password="x", role="user")
    test_db.add(user)
    test_db.flush()
    conv = Conversation(user_id=user.id, title="Old")
    test_db.add(conv)
    test_db.flush()

    old_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
    msg = Message(conversation_id=conv.id, role="user", content="old", created_at=old_time)
    test_db.add(msg)
    test_db.add(
        ModelRun(
            conversation_id=conv.id,
            user_id=user.id,
            assistant_message_id=None,
            task_type="general_qa",
            selected_model="llama-3.1-8b-instant",
            reason_selected="test",
            input_tokens=1,
            output_tokens=1,
            estimated_cost=0.0,
            premium_model_cost=0.0,
            savings_usd=0.0,
            savings_percentage=0.0,
            latency_ms=1.0,
            created_at=old_time,
        )
    )
    test_db.commit()

    metrics = get_admin_user_metrics(
        test_db,
        start_date="2026-01-01",
        end_date="2026-12-31",
        user_id=user.id,
    )
    assert metrics[0].total_prompts == 0
    assert metrics[0].total_tokens == 0
