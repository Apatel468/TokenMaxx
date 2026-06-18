"""
Tests for provider-aware model routing and LiteLLM model resolution.
"""

from config.model_registry import get_provider_for_model, to_litellm_model
from services.groq_models import get_routable_models
from services.model_clients import _provider_for_model
from services.model_scorer import pick_best_model


def test_provider_for_groq_models():
    assert get_provider_for_model("llama-3.1-8b-instant") == "groq"
    assert _provider_for_model("qwen/qwen3-32b") == "groq"


def test_provider_for_openai_and_anthropic_models():
    assert get_provider_for_model("gpt-4o") == "openai"
    assert get_provider_for_model("gpt-4o-mini") == "openai"
    assert get_provider_for_model("o3-mini") == "openai"
    assert get_provider_for_model("claude-3-5-sonnet") == "anthropic"
    assert get_provider_for_model("claude-3-haiku") == "anthropic"


def test_to_litellm_model_prefixes_by_provider():
    assert to_litellm_model("llama-3.1-8b-instant") == "groq/llama-3.1-8b-instant"
    assert to_litellm_model("gpt-4o") == "gpt-4o"
    assert to_litellm_model("o3-mini") == "o3-mini"
    assert to_litellm_model("claude-3-5-sonnet") == (
        "anthropic/claude-3-5-sonnet-20241022"
    )
    assert to_litellm_model("claude-3-haiku") == "anthropic/claude-3-haiku-20240307"


def test_catalog_includes_multi_provider_models():
    catalog = get_routable_models()
    model_ids = {record.model_id for record in catalog}
    assert "gpt-4o" in model_ids
    assert "claude-3-5-sonnet" in model_ids
    providers = {record.provider for record in catalog}
    assert "openai" in providers
    assert "anthropic" in providers
    assert "groq" in providers


def test_scoring_considers_all_providers():
    catalog = get_routable_models()
    winner, scored = pick_best_model(
        "reasoning",
        catalog,
        prompt="Solve this complex logic puzzle step by step and prove your answer.",
    )
    assert winner is not None
    assert len(scored) >= 10
    providers_scored = {candidate.provider for candidate in scored}
    assert "openai" in providers_scored
    assert "anthropic" in providers_scored
    assert winner.model_id in {
        "openai/gpt-oss-120b",
        "o3-mini",
        "gpt-4o",
        "claude-3-5-sonnet",
        "qwen/qwen3-32b",
    }
