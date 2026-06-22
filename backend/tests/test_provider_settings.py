"""
Tests for provider-level model controls.
"""

from config.model_registry import get_provider_for_model
from database import ProviderSetting
from services.model_settings import (
    get_enabled_model_ids,
    get_model_disabled_reason,
    list_model_settings,
    list_provider_settings,
    save_provider_settings,
)
from tests.conftest import auth_headers


def _user_id_from_token(client, auth_token) -> int:
    response = client.get("/auth/me", headers=auth_headers(auth_token))
    return response.json()["id"]


def _make_admin(test_db, email: str = "pytest-user@example.com"):
    from database import User

    user = test_db.query(User).filter(User.email == email).one()
    user.role = "admin"
    test_db.commit()
    return user


def test_provider_settings_default_enabled(test_db):
    rows = list_provider_settings(test_db)
    providers = {row["provider"]: row for row in rows}

    assert "groq" in providers
    assert "openai" in providers
    assert "anthropic" in providers
    assert providers["groq"]["enabled"] is True
    assert providers["groq"]["model_count"] > 0


def test_disabling_provider_disables_all_its_models(test_db, client, auth_token):
    user_id = _user_id_from_token(client, auth_token)

    save_provider_settings(
        test_db,
        [{"provider": "groq", "enabled": False}],
    )

    enabled_ids = get_enabled_model_ids(test_db, user_id)
    groq_models = [
        model_id
        for model_id in enabled_ids
        if get_provider_for_model(model_id) == "groq"
    ]
    assert groq_models == []

    rows = list_model_settings(test_db, user_id, is_admin=False)
    groq_rows = [row for row in rows if row["provider"] == "groq"]
    assert groq_rows
    assert all(row["disabled_by_provider"] for row in groq_rows)
    assert all(not row["available"] for row in groq_rows)


def test_provider_disabled_reason_for_users(test_db, client, auth_token):
    user_id = _user_id_from_token(client, auth_token)
    save_provider_settings(test_db, [{"provider": "groq", "enabled": False}])

    reason = get_model_disabled_reason(test_db, user_id, "llama-3.1-8b-instant")
    assert reason == "Disabled by administrator"


def test_provider_settings_api_get_and_put(client, auth_token, test_db):
    _make_admin(test_db)

    get_resp = client.get("/provider-settings", headers=auth_headers(auth_token))
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert "providers" in body
    assert any(row["provider"] == "groq" for row in body["providers"])

    put_resp = client.put(
        "/provider-settings",
        json={"providers": [{"provider": "groq", "enabled": False}]},
        headers=auth_headers(auth_token),
    )
    assert put_resp.status_code == 200
    groq = next(
        row for row in put_resp.json()["providers"] if row["provider"] == "groq"
    )
    assert groq["enabled"] is False

    row = (
        test_db.query(ProviderSetting)
        .filter(ProviderSetting.provider_name == "groq")
        .one()
    )
    assert row.enabled is False


def test_non_admin_cannot_put_provider_settings(client, auth_token):
    response = client.put(
        "/provider-settings",
        json={"providers": [{"provider": "groq", "enabled": False}]},
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 403


def test_router_ignores_disabled_provider_models(
    client, auth_token, test_db, monkeypatch
):
    _make_admin(test_db)
    save_provider_settings(test_db, [{"provider": "groq", "enabled": False}])

    response = client.post(
        "/chat",
        json={"prompt": "Hello there", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    body = response.json()
    model_id = body.get("selected_model_id") or body.get("selected_model", "")
    assert model_id
    assert get_provider_for_model(model_id) != "groq"
