"""
Tests for JWT authentication routes under /auth.
"""

from tests.conftest import auth_headers


def test_signup_creates_user_and_returns_jwt(client):
    # New accounts should get a bearer token and a user profile with role=user.
    response = client.post(
        "/auth/signup",
        json={"email": "newuser@example.com", "password": "securepass1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "newuser@example.com"
    assert body["user"]["role"] == "user"


def test_signup_rejects_duplicate_email(client):
    # Signing up twice with the same email must fail with 400.
    payload = {"email": "dup@example.com", "password": "securepass1"}
    first = client.post("/auth/signup", json=payload)
    assert first.status_code == 200

    second = client.post("/auth/signup", json=payload)
    assert second.status_code == 400


def test_signup_rejects_short_password(client):
    # Password policy requires at least 8 characters.
    response = client.post(
        "/auth/signup",
        json={"email": "shortpw@example.com", "password": "short"},
    )

    assert response.status_code == 422


def test_login_returns_jwt_for_valid_credentials(client):
    # Login should succeed after signup and return the same shape as signup.
    email = "loginuser@example.com"
    password = "securepass1"
    client.post("/auth/signup", json={"email": email, "password": password})

    response = client.post("/auth/login", json={"email": email, "password": password})

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == email


def test_login_rejects_wrong_password(client):
    # Wrong password must not issue a token.
    email = "badlogin@example.com"
    client.post("/auth/signup", json={"email": email, "password": "securepass1"})

    response = client.post(
        "/auth/login",
        json={"email": email, "password": "wrongpassword"},
    )

    assert response.status_code == 401


def test_me_requires_authentication(client):
    # GET /auth/me without a Bearer token should be rejected.
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_rejects_invalid_token(client):
    # Malformed or bogus JWTs must not authenticate.
    response = client.get(
        "/auth/me",
        headers=auth_headers("not.a.valid.jwt"),
    )

    assert response.status_code == 401


def test_me_returns_profile_for_valid_token(client, auth_token):
    # Valid JWT should resolve to the signed-in user profile from the database.
    response = client.get("/auth/me", headers=auth_headers(auth_token))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "pytest-user@example.com"
    assert body["role"] == "user"
    assert "id" in body
