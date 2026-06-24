"""
Tests for sentiment-aware chat styling helpers and pipeline integration.
"""

from services.context_builder import PromptContext
from services.sentiment_analyzer import SentimentResult, analyze_sentiment
from services.sentiment_context import (
    apply_sentiment_style_to_context,
    build_sentiment_style_instruction,
    resolve_sentiment_for_turn,
)
from tests.conftest import auth_headers


def test_build_sentiment_style_instruction_frustrated():
    instruction = build_sentiment_style_instruction("frustrated")
    assert instruction is not None
    assert "empathy" in instruction.lower()
    assert "concise" in instruction.lower()


def test_build_sentiment_style_instruction_confused():
    instruction = build_sentiment_style_instruction("confused")
    assert instruction is not None
    assert "step-by-step" in instruction.lower()


def test_build_sentiment_style_instruction_urgent():
    instruction = build_sentiment_style_instruction("urgent")
    assert instruction is not None
    assert "actionable" in instruction.lower()


def test_build_sentiment_style_instruction_neutral_returns_none():
    assert build_sentiment_style_instruction("neutral") is None
    assert build_sentiment_style_instruction("unknown") is None
    assert build_sentiment_style_instruction("positive") is None
    assert build_sentiment_style_instruction(None) is None


def test_apply_sentiment_style_updates_system_prompt():
    context = PromptContext(
        prompt="test",
        task_type="general_qa",
        confidence=0.5,
        estimated_input_tokens=10,
        is_long_prompt=False,
        keywords_matched=[],
        system_prompt="You are helpful.",
    )
    sentiment = analyze_sentiment("I'm frustrated — this still isn't working!")
    updated = apply_sentiment_style_to_context(context, sentiment)

    assert updated.sentiment_style_applied is True
    assert updated.sentiment_label == "frustrated"
    assert "User tone guidance" in updated.system_prompt
    assert "empathy" in updated.system_prompt.lower()


def test_apply_sentiment_style_no_op_for_neutral():
    context = PromptContext(
        prompt="test",
        task_type="general_qa",
        confidence=0.5,
        estimated_input_tokens=10,
        is_long_prompt=False,
        keywords_matched=[],
        system_prompt="You are helpful.",
    )
    sentiment = analyze_sentiment("What is the capital of France?")
    updated = apply_sentiment_style_to_context(context, sentiment)

    assert updated.sentiment_style_applied is False
    assert updated.system_prompt == "You are helpful."


def test_resolve_sentiment_for_turn_empty_prompt():
    assert resolve_sentiment_for_turn("   ") is None


def test_chat_includes_sentiment_metadata_when_frustrated(client, auth_token):
    response = client.post(
        "/chat",
        json={
            "prompt": "I'm so frustrated — this keeps failing again!",
            "enhance_prompt": False,
        },
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sentiment_label"] == "frustrated"
    assert body["sentiment_style_applied"] is True
    assert "User tone guidance" in body["system_prompt"]


def test_chat_neutral_prompt_has_no_sentiment_style(client, auth_token):
    response = client.post(
        "/chat",
        json={"prompt": "List three primary colors.", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sentiment_label"] in ("neutral", "")
    assert body["sentiment_style_applied"] is False
    assert "User tone guidance" not in body.get("system_prompt", "")


def test_chat_unchanged_when_sentiment_resolution_fails(client, auth_token, monkeypatch):
    def boom(_prompt: str):
        raise RuntimeError("sentiment unavailable")

    monkeypatch.setattr(
        "services.chat_service.resolve_sentiment_for_turn",
        lambda _prompt: None,
    )

    response = client.post(
        "/chat",
        json={"prompt": "I'm frustrated!", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sentiment_style_applied"] is False
    assert body["mock_response"] == "Mocked LLM response for testing."
