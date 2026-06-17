"""
Tests for user API keys — encryption, masking, isolation, and test endpoint.
"""

from __future__ import annotations

from database import UserApiKey
from services.key_encryption import decrypt_api_key, encrypt_api_key, mask_api_key
from tests.conftest import auth_headers


def _signup(client, email: str) -> str:
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "testpass123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_api_key_encrypted_at_rest(client, auth_token, test_db):
    response = client.post(
        "/user/api-keys",
        json={
            "provider": "groq",
            "api_key": "gsk-test-secret-key-value",
            "key_label": "My Groq",
        },
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["masked_key"] == mask_api_key("gsk-test-secret-key-value")
    assert "gsk-test-secret-key-value" not in body["masked_key"] or "..." in body["masked_key"]

    row = test_db.query(UserApiKey).filter(UserApiKey.id == body["id"]).first()
    assert row is not None
    assert row.encrypted_api_key != "gsk-test-secret-key-value"
    assert decrypt_api_key(row.encrypted_api_key) == "gsk-test-secret-key-value"


def test_api_key_response_is_masked(client, auth_token):
    response = client.post(
        "/user/api-keys",
        json={
            "provider": "openai",
            "api_key": "sk-proj-abcdefghijklmnop",
            "key_label": "OpenAI",
        },
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 201
    listed = client.get("/user/api-keys", headers=auth_headers(auth_token))
    assert listed.status_code == 200
    key_row = listed.json()[0]
    assert key_row["masked_key"].startswith("sk-")
    assert "sk-proj-abcdefghijklmnop" not in str(listed.json())


def test_user_cannot_access_other_users_keys(client):
    token_a = _signup(client, "keys-a@example.com")
    token_b = _signup(client, "keys-b@example.com")

    created = client.post(
        "/user/api-keys",
        json={"provider": "groq", "api_key": "gsk-user-a-secret-key", "key_label": "A"},
        headers=auth_headers(token_a),
    )
    assert created.status_code == 201
    key_id = created.json()["id"]

    delete_b = client.delete(
        f"/user/api-keys/{key_id}",
        headers=auth_headers(token_b),
    )
    assert delete_b.status_code == 404

    list_b = client.get("/user/api-keys", headers=auth_headers(token_b))
    assert list_b.json() == []


def test_api_key_test_endpoint_mocked(client, auth_token, monkeypatch):
    client.post(
        "/user/api-keys",
        json={"provider": "groq", "api_key": "gsk-valid-looking-key", "key_label": "Groq"},
        headers=auth_headers(auth_token),
    )
    listed = client.get("/user/api-keys", headers=auth_headers(auth_token))
    key_id = listed.json()[0]["id"]

    import routers.user_api_keys as keys_router

    monkeypatch.setattr(
        keys_router,
        "test_provider_api_key",
        lambda provider, api_key: {
            "valid": True,
            "provider": provider,
            "message": "API key is valid.",
        },
    )

    test_response = client.post(
        f"/user/api-keys/{key_id}/test",
        headers=auth_headers(auth_token),
    )
    assert test_response.status_code == 200
    assert test_response.json()["valid"] is True
