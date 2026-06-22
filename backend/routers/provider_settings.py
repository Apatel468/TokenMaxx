"""
Provider settings router — org-wide provider enable/disable toggles.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import User, get_db
from models import ProviderSettingsResponse, ProviderSettingsUpdate, ProviderSettingItem
from services.auth_dependencies import get_current_user, require_admin
from services.model_settings import list_provider_settings, save_provider_settings

router = APIRouter(prefix="/provider-settings", tags=["provider-settings"])


@router.get("", response_model=ProviderSettingsResponse)
def get_provider_settings(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ProviderSettingsResponse:
    """All catalog providers with enabled state and model counts."""
    rows = list_provider_settings(db)
    return ProviderSettingsResponse(
        providers=[ProviderSettingItem(**row) for row in rows]
    )


@router.put("", response_model=ProviderSettingsResponse)
def put_provider_settings(
    body: ProviderSettingsUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ProviderSettingsResponse:
    """UPSERT organization-wide provider toggles (admin only)."""
    updates = [item.model_dump() for item in body.providers]
    rows = save_provider_settings(db, updates)
    return ProviderSettingsResponse(
        providers=[ProviderSettingItem(**row) for row in rows]
    )
