"""
User API key storage, encryption, resolution, and provider testing.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from database import UserApiKey
from services.key_encryption import decrypt_api_key, encrypt_api_key, mask_api_key

SUPPORTED_PROVIDERS = ("groq", "openai", "anthropic", "google", "bedrock")

PROVIDER_ENV_KEYS: dict[str, str] = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GEMINI_API_KEY",
    "bedrock": "AWS_ACCESS_KEY_ID",
}

# LiteLLM model used for lightweight key validation
_PROVIDER_TEST_MODELS: dict[str, str] = {
    "groq": "groq/llama-3.1-8b-instant",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-haiku-20240307",
    "google": "gemini/gemini-1.5-flash",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider. Use one of: {', '.join(SUPPORTED_PROVIDERS)}",
        )
    return normalized


def env_api_key(provider: str) -> str | None:
    """App-level key from environment."""
    env_name = PROVIDER_ENV_KEYS.get(provider)
    if not env_name:
        return None
    value = os.getenv(env_name, "").strip()
    return value or None


def list_user_api_keys(db: Session, user_id: int) -> list[UserApiKey]:
    return (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user_id)
        .order_by(UserApiKey.created_at.desc())
        .all()
    )


def get_user_api_key_or_404(db: Session, user_id: int, key_id: int) -> UserApiKey:
    row = (
        db.query(UserApiKey)
        .filter(UserApiKey.id == key_id, UserApiKey.user_id == user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    return row


def create_user_api_key(
    db: Session,
    user_id: int,
    *,
    provider: str,
    api_key: str,
    key_label: str = "",
    is_active: bool = True,
) -> UserApiKey:
    provider = validate_provider(provider)
    plain = api_key.strip()
    if len(plain) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key is too short.",
        )

    row = UserApiKey(
        user_id=user_id,
        provider=provider,
        encrypted_api_key=encrypt_api_key(plain),
        key_label=key_label.strip() or provider.title(),
        is_active=is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_user_api_key(
    db: Session,
    user_id: int,
    key_id: int,
    *,
    api_key: str | None = None,
    key_label: str | None = None,
    is_active: bool | None = None,
) -> UserApiKey:
    row = get_user_api_key_or_404(db, user_id, key_id)
    if api_key is not None:
        plain = api_key.strip()
        if len(plain) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API key is too short.",
            )
        row.encrypted_api_key = encrypt_api_key(plain)
    if key_label is not None:
        row.key_label = key_label.strip() or row.key_label
    if is_active is not None:
        row.is_active = is_active
    row.updated_at = _utcnow()
    db.commit()
    db.refresh(row)
    return row


def delete_user_api_key(db: Session, user_id: int, key_id: int) -> None:
    row = get_user_api_key_or_404(db, user_id, key_id)
    db.delete(row)
    db.commit()


def get_active_decrypted_key(db: Session, user_id: int, provider: str) -> str | None:
    """Return decrypted user key for provider if active."""
    provider = provider.strip().lower()
    row = (
        db.query(UserApiKey)
        .filter(
            UserApiKey.user_id == user_id,
            UserApiKey.provider == provider,
            UserApiKey.is_active.is_(True),
        )
        .order_by(UserApiKey.updated_at.desc())
        .first()
    )
    if not row:
        return None
    return decrypt_api_key(row.encrypted_api_key)


def mark_provider_key_used(db: Session, user_id: int, provider: str) -> None:
    row = (
        db.query(UserApiKey)
        .filter(
            UserApiKey.user_id == user_id,
            UserApiKey.provider == provider,
            UserApiKey.is_active.is_(True),
        )
        .order_by(UserApiKey.updated_at.desc())
        .first()
    )
    if row:
        row.last_used_at = _utcnow()
        db.commit()


def resolve_api_key(db: Session | None, user_id: int | None, provider: str) -> str | None:
    """User key first, then app-level environment key."""
    provider = provider.strip().lower()
    if db is not None and user_id is not None:
        user_key = get_active_decrypted_key(db, user_id, provider)
        if user_key:
            return user_key
    return env_api_key(provider)


def masked_key_preview(row: UserApiKey) -> str:
    try:
        plain = decrypt_api_key(row.encrypted_api_key)
    except ValueError:
        return "***"
    return mask_api_key(plain)


def test_provider_api_key(provider: str, api_key: str) -> dict:
    """Validate a provider API key with a minimal LiteLLM call."""
    provider = validate_provider(provider)
    plain = api_key.strip()
    if len(plain) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key is too short.",
        )

    if provider == "bedrock":
        return {
            "valid": False,
            "provider": provider,
            "message": "AWS Bedrock key testing is not implemented yet (placeholder).",
        }

    model = _PROVIDER_TEST_MODELS.get(provider)
    if not model:
        return {"valid": False, "provider": provider, "message": "No test model configured."}

    try:
        import litellm

        litellm.completion(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            api_key=plain,
        )
        return {"valid": True, "provider": provider, "message": "API key is valid."}
    except Exception as exc:
        return {
            "valid": False,
            "provider": provider,
            "message": f"Key test failed: {exc}",
        }
