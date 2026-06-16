"""
Tests for LLM prompt classification and routing integration.
"""

from services.llm_classifier import LLMClassificationResult
from services.prompt_analyzer import AnalysisResult, analyze_prompt, _analyze_with_rules
from tests.conftest import auth_headers


def test_llm_classification_success(monkeypatch):
    # When the LLM classifier succeeds, analyze_prompt should use its output.
    def fake_llm_classify(prompt: str) -> LLMClassificationResult:
        assert "fibonacci" in prompt.lower()
        return LLMClassificationResult(
            task_type="coding",
            confidence=0.92,
            reason="The user is asking for a programming implementation.",
        )

    monkeypatch.setattr(
        "services.prompt_analyzer.classify_prompt_with_llm",
        fake_llm_classify,
    )

    result = analyze_prompt("Write a Python function for fibonacci numbers.")

    assert result.task_type == "coding"
    assert result.confidence == 0.92
    assert result.classification_method == "llm"
    assert "programming" in result.classification_reason.lower()


def test_llm_classifier_falls_back_to_rules(monkeypatch):
    # When the LLM path fails, keyword rules should classify the prompt.
    def failing_llm(_prompt: str) -> LLMClassificationResult:
        raise RuntimeError("Groq unavailable")

    monkeypatch.setattr(
        "services.prompt_analyzer.classify_prompt_with_llm",
        failing_llm,
    )

    result = analyze_prompt("Summarize this article in bullet points.")

    assert result.classification_method == "rule_fallback"
    assert result.task_type == "summarization"
    assert result.confidence > 0
    assert result.classification_reason


def test_rule_classifier_maps_coding_keywords():
    # Baseline rule classifier still handles coding prompts directly.
    result = _analyze_with_rules("Debug this Python function syntax error.")

    assert result.task_type == "coding"
    assert result.classification_method == "rule_fallback"
    assert result.keywords_matched


def test_router_uses_llm_classifier_task_type(client, auth_token, monkeypatch):
    # POST /chat should route using the LLM-produced task_type.
    def fake_llm_classify(_prompt: str) -> LLMClassificationResult:
        return LLMClassificationResult(
            task_type="math",
            confidence=0.88,
            reason="The prompt asks for a numerical calculation.",
        )

    monkeypatch.setattr(
        "services.prompt_analyzer.classify_prompt_with_llm",
        fake_llm_classify,
    )

    response = client.post(
        "/chat",
        json={"prompt": "What is the integral of x^2?", "enhance_prompt": False},
        headers=auth_headers(auth_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_type"] == "math"
    assert body["classification_method"] == "llm"
    assert body["classification_confidence"] == 0.88
    assert body["classification_reason"]
