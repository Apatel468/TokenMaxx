"""
Auth Service — signup, login, password hashing, and JWT tokens.

Passwords are NEVER stored in plain text — only bcrypt hashes in the users table.
JWTs let the frontend stay logged in across page refreshes and devices.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from database import User

# Read from .env in production; dev default is fine for local demos only
JWT_SECRET = os.getenv("JWT_SECRET", "tokenmaxx-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "168"))  # 7 days


def hash_password(plain_password: str) -> str:
    """Turn a plain password into a bcrypt hash (safe to store in SQLite)."""
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True when the plain password matches the stored hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, email: str, role: str) -> str:
    """Build a signed JWT the client sends as: Authorization: Bearer <token>."""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Validate JWT signature and expiry; raise HTTP 401 if invalid."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired — please log in again.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing session token.",
        ) from exc


def register_user(db: Session, email: str, password: str, role: str = "user") -> User:
    """Create a new user row after checking the email is not taken."""
    normalized = email.strip().lower()
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters.",
        )

    existing = db.query(User).filter(User.email == normalized).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already exists. Please log in.",
        )

    user = User(
        email=normalized,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    db.flush()  # assign user.id before we build the JWT
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Verify email + password and return the user (login only — not used for signup)."""
    normalized = email.strip().lower()
    user = db.query(User).filter(User.email == normalized).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found. Please sign up.",
        )
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password.",
        )
    return user


def ensure_seed_admin(db: Session) -> None:
    """
    Create the first admin from ADMIN_EMAIL + ADMIN_PASSWORD in .env (optional).

    Only runs when those env vars are set and no user exists with that email.
    """
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not admin_email or not admin_password:
        return

    existing = db.query(User).filter(User.email == admin_email).first()
    if existing:
        if existing.role != "admin":
            existing.role = "admin"
            db.commit()
        return

    db.add(
        User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            role="admin",
        )
    )
    db.commit()
