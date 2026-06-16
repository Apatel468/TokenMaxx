"""
Shared pytest fixtures for TokenMaxx backend tests.

Each test run uses an isolated SQLite file (tmp_path) so the real
smartllm_router.db is never touched. LLM calls are mocked so no API key
or tokens are required.
"""

from __future__ import annotations

import os

# Force test-safe env before main/database load .env with real secrets.
os.environ["GROQ_API_KEY"] = ""
os.environ["ADMIN_EMAIL"] = ""
os.environ["ADMIN_PASSWORD"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.model_clients import ModelResponse


def _mock_generate_response(groq_model: str, context, messages=None) -> ModelResponse:
    """Deterministic stand-in for Groq/LiteLLM — no network or API key."""
    return ModelResponse(
        text="Mocked LLM response for testing.",
        estimated_output_tokens=12,
        input_tokens=10,
        is_mock=True,
        latency_ms=1.0,
        litellm_model="mock/test",
    )


def _mock_stream_response(groq_model: str, context, messages=None):
    """Yield the same mocked text in word-sized chunks."""
    text = "Mocked LLM response for testing."
    words = text.split()
    for index, word in enumerate(words):
        yield word if index == 0 else f" {word}"


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """
    Point SQLAlchemy at a fresh SQLite file for this test.

    Patches database.engine and SessionLocal before the app lifespan runs.
    """
    import database as db_module
    import services.groq_models as groq_models

    groq_models._catalog_cache = None

    db_file = tmp_path / "test.db"
    url = f"sqlite:///{db_file}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )

    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", TestingSessionLocal)
    db_module.init_db()

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(test_db, monkeypatch):
    """
    FastAPI TestClient with isolated DB and mocked LLM calls.
    """
    import services.model_clients as model_clients
    import services.regenerate_service as regenerate_service

    monkeypatch.setattr(model_clients, "generate_response", _mock_generate_response)
    monkeypatch.setattr(model_clients, "stream_response", _mock_stream_response)
    monkeypatch.setattr(
        regenerate_service, "generate_response", _mock_generate_response
    )

    # Import main after patches; chat router holds direct imports.
    import routers.chat as chat_router

    monkeypatch.setattr(chat_router, "generate_response", _mock_generate_response)
    monkeypatch.setattr(chat_router, "stream_response", _mock_stream_response)

    import main

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def auth_token(client) -> str:
    """Sign up a throwaway user and return a Bearer token."""
    response = client.post(
        "/auth/signup",
        json={"email": "pytest-user@example.com", "password": "testpass123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    """Build Authorization header for protected routes."""
    return {"Authorization": f"Bearer {token}"}
