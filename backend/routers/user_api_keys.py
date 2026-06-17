"""
User API keys router — CRUD and test for per-user LLM provider keys.
"""

from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import User, get_db
from models import (
    ApiKeyTestResult,
    UserApiKeyCreate,
    UserApiKeyOut,
    UserApiKeyUpdate,
)
from services.activity_log_service import record_activity
from services.api_key_service import (
    create_user_api_key,
    delete_user_api_key,
    get_user_api_key_or_404,
    list_user_api_keys,
    masked_key_preview,
    test_provider_api_key,
    update_user_api_key,
    validate_provider,
)
from services.auth_dependencies import get_current_user

router = APIRouter(prefix="/user/api-keys", tags=["user-api-keys"])


def _format_dt(dt) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _to_out(row) -> UserApiKeyOut:
    return UserApiKeyOut(
        id=row.id,
        provider=row.provider,
        key_label=row.key_label,
        masked_key=masked_key_preview(row),
        is_active=row.is_active,
        created_at=_format_dt(row.created_at),
        updated_at=_format_dt(row.updated_at),
        last_used_at=_format_dt(row.last_used_at) if row.last_used_at else None,
    )


@router.get("", response_model=list[UserApiKeyOut])
def get_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserApiKeyOut]:
    rows = list_user_api_keys(db, current_user.id)
    return [_to_out(row) for row in rows]


@router.post("", response_model=UserApiKeyOut, status_code=status.HTTP_201_CREATED)
def add_api_key(
    body: UserApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserApiKeyOut:
    provider = validate_provider(body.provider)
    row = create_user_api_key(
        db,
        current_user.id,
        provider=provider,
        api_key=body.api_key,
        key_label=body.key_label,
        is_active=body.is_active,
    )
    record_activity(
        db,
        user_id=current_user.id,
        event_type="api_key_added",
        message=f"API key added for provider {provider}.",
        metadata={"provider": provider, "key_label": row.key_label},
    )
    db.commit()
    return _to_out(row)


@router.put("/{key_id}", response_model=UserApiKeyOut)
def update_api_key(
    key_id: int,
    body: UserApiKeyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserApiKeyOut:
    row = update_user_api_key(
        db,
        current_user.id,
        key_id,
        api_key=body.api_key,
        key_label=body.key_label,
        is_active=body.is_active,
    )
    return _to_out(row)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    row = get_user_api_key_or_404(db, current_user.id, key_id)
    provider = row.provider
    delete_user_api_key(db, current_user.id, key_id)
    record_activity(
        db,
        user_id=current_user.id,
        event_type="api_key_deleted",
        message=f"API key deleted for provider {provider}.",
        metadata={"provider": provider, "key_id": key_id},
    )
    db.commit()


@router.post("/{key_id}/test", response_model=ApiKeyTestResult)
def test_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiKeyTestResult:
    from services.key_encryption import decrypt_api_key

    row = get_user_api_key_or_404(db, current_user.id, key_id)
    plain = decrypt_api_key(row.encrypted_api_key)
    result = test_provider_api_key(row.provider, plain)
    record_activity(
        db,
        user_id=current_user.id,
        event_type="api_key_tested",
        level="info" if result["valid"] else "warning",
        message=result["message"],
        metadata={"provider": row.provider, "valid": result["valid"]},
    )
    db.commit()
    return ApiKeyTestResult(**result)
