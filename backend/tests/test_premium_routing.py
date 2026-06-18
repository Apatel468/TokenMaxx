"""
Tests for premium vs economy routing with provider key availability.
"""

import pytest

from services.groq_models import get_routable_models, sync_groq_catalog
from services.model_scorer import infer_task_type_from_prompt, pick_best_model
from services.router_engine import route

BUSINESS_PROMPT = (
    "Write a detailed business strategy for a Fortune 500 company"
)


@pytest.fixture(autouse=True)
def fresh_catalog():
    sync_groq_catalog(force=True)


@pytest.fixture
def groq_only_keys(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-groq-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def all_provider_keys(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-groq-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-anthropic-key")


def test_infer_business_task_from_strategy_prompt():
    assert infer_task_type_from_prompt(BUSINESS_PROMPT, "general_qa") == "business"


def test_simple_qa_prefers_cheap_model_with_premium_keys(all_provider_keys):
    catalog = get_routable_models()
    winner, _ = pick_best_model(
        "general_qa",
        catalog,
        prompt="What is photosynthesis?",
        db=None,
        user_id=None,
    )
    assert winner is not None
    assert winner.model_id in {"llama-3.1-8b-instant", "openai/gpt-oss-20b"}


def test_general_qa_does_not_pick_gpt4o(all_provider_keys):
    catalog = get_routable_models()
    winner, scored = pick_best_model(
        "general_qa",
        catalog,
        prompt="What is the capital of France?",
        db=None,
        user_id=None,
    )
    assert winner.model_id != "gpt-4o"
    assert winner.model_id != "claude-3-5-sonnet"
    gpt_row = next((c for c in scored if c.model_id == "gpt-4o"), None)
    assert gpt_row is not None
    assert gpt_row.task_preference_bonus < 0


def test_business_strategy_prefers_premium_with_keys(all_provider_keys):
    catalog = get_routable_models()
    winner, _ = pick_best_model(
        "business",
        catalog,
        prompt=BUSINESS_PROMPT,
        db=None,
        user_id=None,
    )
    assert winner.model_id in {"gpt-4o", "claude-3-5-sonnet"}


def test_business_strategy_falls_back_to_groq_without_premium_keys(groq_only_keys):
    catalog = get_routable_models()
    winner, _ = pick_best_model(
        "business",
        catalog,
        prompt=BUSINESS_PROMPT,
        db=None,
        user_id=None,
    )
    assert winner.provider == "groq"
    assert winner.model_id in {
        "llama-3.3-70b-versatile",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "openai/gpt-oss-120b",
    }


def test_coding_prefers_qwen_or_premium(all_provider_keys):
    catalog = get_routable_models()
    winner, _ = pick_best_model(
        "coding",
        catalog,
        prompt="Debug this React component that throws a hooks error on re-render.",
        db=None,
        user_id=None,
    )
    assert winner.model_id in {
        "qwen/qwen3-32b",
        "gpt-4o",
        "claude-3-5-sonnet",
        "o3-mini",
    }


def test_route_business_includes_explanation(client, auth_token, test_db, all_provider_keys):
    from database import User
    from services.context_builder import build_context
    from services.prompt_analyzer import AnalysisResult
    from tests.conftest import auth_headers

    analysis = AnalysisResult(
        task_type="business",
        confidence=0.9,
        keywords_matched=["business strategy"],
        classification_reason="test",
    )
    context = build_context(BUSINESS_PROMPT, analysis, enhance_prompt_enabled=False)
    user = test_db.query(User).filter(User.email == "pytest-user@example.com").one()
    decision = route(context, test_db, user.id)

    assert decision.task_type == "business"
    assert decision.complexity_score >= 0.35
    assert decision.routing_explanation
    assert decision.provider_availability.get("openai") is True
    assert decision.model_id in {"gpt-4o", "claude-3-5-sonnet"}

    response = client.post(
        "/chat",
        json={"prompt": BUSINESS_PROMPT, "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("complexity_level") in {"medium", "high"}
    assert body.get("routing_explanation")
