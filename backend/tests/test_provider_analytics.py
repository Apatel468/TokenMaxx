"""Tests for GET /analytics/provider-usage."""

from database import Conversation, Message, ModelRun, User
from tests.conftest import auth_headers


def test_provider_usage_aggregation(client, auth_token, test_db):
    client.post(
        "/chat",
        json={"prompt": "Hello provider analytics", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )

    response = client.get("/analytics/provider-usage", headers=auth_headers(auth_token))
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    groq_row = next((row for row in body if row["provider"] == "groq"), None)
    assert groq_row is not None
    assert groq_row["run_count"] >= 1
    assert groq_row["total_tokens"] >= 0


def test_provider_usage_from_stored_runs(test_db):
    from services.report_generator import get_provider_usage

    user = User(email="provider-analytics@example.com", hashed_password="x", role="user")
    test_db.add(user)
    test_db.flush()
    conv = Conversation(user_id=user.id, title="Test")
    test_db.add(conv)
    test_db.flush()

    test_db.add_all(
        [
            ModelRun(
                conversation_id=conv.id,
                user_id=user.id,
                assistant_message_id=None,
                task_type="general_qa",
                selected_model="gpt-4o",
                provider="openai",
                reason_selected="test",
                input_tokens=10,
                output_tokens=20,
                estimated_cost=0.01,
                premium_model_cost=0.05,
                savings_usd=0.04,
                savings_percentage=80.0,
                latency_ms=100.0,
            ),
            ModelRun(
                conversation_id=conv.id,
                user_id=user.id,
                assistant_message_id=None,
                task_type="coding",
                selected_model="llama-3.1-8b-instant",
                provider="groq",
                reason_selected="test",
                input_tokens=5,
                output_tokens=5,
                estimated_cost=0.001,
                premium_model_cost=0.01,
                savings_usd=0.009,
                savings_percentage=90.0,
                latency_ms=50.0,
            ),
        ]
    )
    test_db.commit()

    rows = get_provider_usage(test_db, user.id)
    by_provider = {row.provider: row for row in rows}
    assert by_provider["openai"].run_count == 1
    assert by_provider["groq"].run_count == 1
    assert by_provider["openai"].model_count == 1
