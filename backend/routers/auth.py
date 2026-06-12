"""
Auth router — signup, login, logout, and current-user profile.

POST /auth/signup  → create account (role defaults to "user")
POST /auth/login   → returns JWT access token
POST /auth/logout  → client should discard token (stateless JWT)
GET  /auth/me      → who am I? (requires Bearer token)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import User, get_db
from models import AuthResponse, LoginRequest, SignupRequest, UserOut
from services.auth_dependencies import get_current_user
from services.auth_service import authenticate_user, create_access_token, register_user
from services.timezone_utils import format_timestamp_eastern

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User, db: Session) -> UserOut:
    from services.user_preferences import get_enhance_prompts

    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        created_at=format_timestamp_eastern(user.created_at),
        enhance_prompts=get_enhance_prompts(db, user.id),
    )


def _auth_response(user: User, db: Session) -> AuthResponse:
    token = create_access_token(user.id, user.email, user.role)
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=_user_out(user, db),
    )


@router.post("/signup", response_model=AuthResponse)
def signup(body: SignupRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Register a new user and return a JWT so they are logged in immediately."""
    user = register_user(db, body.email, body.password, role="user")
    return _auth_response(user, db)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Verify email/password and return a JWT session token."""
    user = authenticate_user(db, body.email, body.password)
    return _auth_response(user, db)


@router.post("/logout")
def logout() -> dict:
    """
    Logout is handled on the client by deleting the stored JWT.

    We keep this endpoint so the frontend has a clear logout action.
    """
    return {"message": "Logged out. Discard your token on the client."}


@router.get("/me", response_model=UserOut)
def me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    """Return the logged-in user's profile (validates the JWT)."""
    return _user_out(current_user, db)
