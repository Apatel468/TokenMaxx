"""
MVP encryption for user API keys at rest.

Uses Fernet symmetric encryption. Secret from API_KEY_ENCRYPTION_SECRET,
or derived from JWT_SECRET when unset (document as MVP-level security).
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

_SENSITIVE_SUBSTRINGS = ("api_key", "password", "token", "secret", "authorization")


def _encryption_secret() -> str:
    explicit = os.getenv("API_KEY_ENCRYPTION_SECRET", "").strip()
    if explicit:
        return explicit
    return os.getenv("JWT_SECRET", "tokenmaxx-dev-secret-change-in-production")


def _fernet() -> Fernet:
    digest = hashlib.sha256(_encryption_secret().encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt a raw API key for database storage."""
    return _fernet().encrypt(plain_key.strip().encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt a stored API key."""
    try:
        return _fernet().decrypt(encrypted_key.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Could not decrypt API key.") from exc


def mask_api_key(plain_key: str) -> str:
    """Return a masked preview like sk-...abcd."""
    key = plain_key.strip()
    if len(key) <= 8:
        return "***"
    if len(key) <= 12:
        return f"{key[:2]}...{key[-2:]}"
    return f"{key[:3]}...{key[-4:]}"


def redact_sensitive_value(key: str, value) -> object:
    """Redact values that look like secrets for activity log metadata."""
    lower = key.lower()
    if any(part in lower for part in _SENSITIVE_SUBSTRINGS):
        if isinstance(value, str) and value.strip():
            return mask_api_key(value)
        return "[redacted]"
    return value
