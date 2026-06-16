"""
Tests for per-user model preference sync and defaults.
"""

from config.model_registry import GROQ_CHAT_MODEL_IDS
from database import UserModelSetting
from services.model_settings import (
    get_model_disabled_reason,
    list_model_settings,
    sync_user_model_settings,
)
from tests.conftest import auth_headers


def _user_id_from_token(client, auth_token) -> int:
    response = client.get("/auth/me", headers=auth_headers(auth_token))
    return response.json()["id"]


def test_routable_models_enabled_by_default(client, auth_token, test_db):
    # Fresh users should see every chat-routable model as available.
    user_id = _user_id_from_token(client, auth_token)
    sync_user_model_settings(test_db, user_id)

    rows = list_model_settings(test_db, user_id, is_admin=False)
    routable_ids = set(GROQ_CHAT_MODEL_IDS)

    assert {row["model_id"] for row in rows} == routable_ids
    assert all(row["user_enabled"] for row in rows)
    assert all(row["available"] for row in rows)
    assert "llama-3.1-8b-instant" in routable_ids
    llama = next(r for r in rows if r["model_id"] == "llama-3.1-8b-instant")
    assert llama["user_enabled"] is True
    assert get_model_disabled_reason(test_db, user_id, "llama-3.1-8b-instant") is None


def test_non_routable_models_not_enabled_for_user(client, auth_token, test_db):
    # Audio-only models like whisper must not appear in user chat preferences.
    user_id = _user_id_from_token(client, auth_token)
    test_db.add(
        UserModelSetting(
            user_id=user_id,
            model_id="whisper-large-v3",
            enabled=True,
            explicitly_set=False,
        )
    )
    test_db.commit()

    sync_user_model_settings(test_db, user_id)

    stored_ids = {
        row.model_id
        for row in test_db.query(UserModelSetting)
        .filter(UserModelSetting.user_id == user_id)
        .all()
    }
    assert "whisper-large-v3" not in stored_ids
    assert stored_ids.issubset(GROQ_CHAT_MODEL_IDS)


def test_sync_backfills_missing_without_overwriting_explicit_disable(
    client, auth_token, test_db
):
    # Missing rows are backfilled; explicit user disables are preserved.
    user_id = _user_id_from_token(client, auth_token)
    test_db.query(UserModelSetting).filter(
        UserModelSetting.user_id == user_id
    ).delete()
    test_db.add(
        UserModelSetting(
            user_id=user_id,
            model_id="llama-3.1-8b-instant",
            enabled=False,
            explicitly_set=True,
        )
    )
    test_db.commit()

    sync_user_model_settings(test_db, user_id)

    rows = {
        row.model_id: row
        for row in test_db.query(UserModelSetting)
        .filter(UserModelSetting.user_id == user_id)
        .all()
    }
    assert rows["llama-3.1-8b-instant"].enabled is False
    assert rows["llama-3.1-8b-instant"].explicitly_set is True
    assert "llama-3.3-70b-versatile" in rows
    assert rows["llama-3.3-70b-versatile"].enabled is True
    assert get_model_disabled_reason(test_db, user_id, "llama-3.1-8b-instant") == (
        "Disabled in your preferences"
    )


def test_implicit_disabled_rows_are_repaired(client, auth_token, test_db):
    # Legacy/bad rows with enabled=False but never saved should be cleared.
    user_id = _user_id_from_token(client, auth_token)
    test_db.query(UserModelSetting).filter(
        UserModelSetting.user_id == user_id
    ).delete()
    test_db.add(
        UserModelSetting(
            user_id=user_id,
            model_id="llama-3.1-8b-instant",
            enabled=False,
            explicitly_set=False,
        )
    )
    test_db.commit()

    sync_user_model_settings(test_db, user_id)

    row = (
        test_db.query(UserModelSetting)
        .filter(
            UserModelSetting.user_id == user_id,
            UserModelSetting.model_id == "llama-3.1-8b-instant",
        )
        .first()
    )
    assert row is not None
    assert row.enabled is True
    assert get_model_disabled_reason(test_db, user_id, "llama-3.1-8b-instant") is None
