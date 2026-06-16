"""
Tests for chat routing (POST /chat) and regeneration (POST /chat/regenerate).

LLM calls are mocked in conftest — these tests verify HTTP auth, routing
pipeline wiring, and persistence without calling Groq.
"""

from tests.conftest import auth_headers


def test_chat_requires_authentication(client):
    # POST /chat is protected; anonymous requests must get 401.
    response = client.post("/chat", json={"prompt": "Hello?"})

    assert response.status_code == 401


def test_chat_routes_prompt_and_returns_mock_response(client, auth_token):
    # Authenticated chat should run the router pipeline and return a mocked reply.
    response = client.post(
        "/chat",
        json={"prompt": "What is 2 + 2?", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mock_response"] == "Mocked LLM response for testing."
    assert body["conversation_id"] > 0
    assert body["user_message_id"] > 0
    assert body["assistant_message_id"] > 0
    assert body["selected_model_id"]
    assert body["task_type"]


def test_chat_continues_existing_conversation(client, auth_token):
    # A second message with conversation_id should append to the same thread.
    first = client.post(
        "/chat",
        json={"prompt": "First message", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )
    assert first.status_code == 200
    conversation_id = first.json()["conversation_id"]

    second = client.post(
        "/chat",
        json={
            "prompt": "Follow-up question",
            "conversation_id": conversation_id,
            "enhance_prompt": False,
        },
        headers=auth_headers(auth_token),
    )

    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id


def test_regenerate_requires_authentication(client):
    # POST /chat/regenerate is protected like POST /chat.
    response = client.post(
        "/chat/regenerate",
        json={
            "conversation_id": 1,
            "message_id": 1,
            "model_id": "llama-3.3-70b-versatile",
        },
    )

    assert response.status_code == 401


def test_regenerate_with_user_selected_model(client, auth_token):
    # After an initial chat turn, regenerate should produce a new mocked reply.
    chat_response = client.post(
        "/chat",
        json={"prompt": "Explain pytest briefly.", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )
    assert chat_response.status_code == 200
    chat_body = chat_response.json()

    # Pick a different routable model when possible; fall back to the routed one.
    model_id = chat_body["selected_model_id"]
    candidates = [
        rec["model_id"]
        for rec in chat_body.get("top_recommendations", [])
        if rec.get("available")
    ]
    if candidates:
        model_id = candidates[0]

    regen_response = client.post(
        "/chat/regenerate",
        json={
            "conversation_id": chat_body["conversation_id"],
            "message_id": chat_body["user_message_id"],
            "model_id": model_id,
        },
        headers=auth_headers(auth_token),
    )

    assert regen_response.status_code == 200
    regen_body = regen_response.json()
    assert regen_body["response"] == "Mocked LLM response for testing."
    assert regen_body["model_used"] == model_id
    assert regen_body["was_user_selected"] is True
    assert regen_body["task_type"]
    assert regen_body["regeneration_reason"]
    assert model_id in regen_body["regeneration_reason"] or regen_body.get("model_label")
    assert regen_body["actual_cost"] >= 0
    assert regen_body["premium_cost"] >= 0
    assert regen_body["input_tokens"] >= 0
    assert regen_body["output_tokens"] >= 0
    assert regen_body["assistant_message_id"] > chat_body["assistant_message_id"]
    assert regen_body["response_label"] == "User Selected Model"
