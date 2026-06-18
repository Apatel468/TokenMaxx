"""
Model Registry — curated metadata for all providers allowed in TokenMaxx.

Models in MODEL_ALLOWLIST are synced, routed, and shown in Model Controls.
Chat routing uses CHAT_MODEL_IDS (excludes whisper-large-v3).
"""

from __future__ import annotations

from typing import Literal, TypedDict

ProviderName = Literal["groq", "openai", "anthropic", "google"]

# Groq-hosted models (checked against live Groq API when GROQ_API_KEY is set)
GROQ_MODEL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "qwen/qwen3-32b",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "whisper-large-v3",
    }
)

# All routable / catalog models across providers
MODEL_ALLOWLIST: frozenset[str] = GROQ_MODEL_ALLOWLIST | frozenset(
    {
        "gpt-4o-mini",
        "gpt-4o",
        "o3-mini",
        "claude-3-5-sonnet",
        "claude-3-haiku",
    }
)

# Chat-completion models eligible for routing / Model Controls toggles
CHAT_MODEL_IDS: frozenset[str] = frozenset(MODEL_ALLOWLIST - {"whisper-large-v3"})

# Backward-compatible aliases
GROQ_CHAT_MODEL_IDS: frozenset[str] = CHAT_MODEL_IDS
GROQ_AUDIO_MODEL_IDS: frozenset[str] = frozenset({"whisper-large-v3"})

# Registry id → LiteLLM model string (when different from default provider prefixing)
LITELLM_MODEL_IDS: dict[str, str] = {
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3-haiku": "claude-3-haiku-20240307",
}


class CostPer1M(TypedDict):
    input: float
    output: float


class ModelMetadata(TypedDict):
    model_name: str
    provider: ProviderName
    cost_per_1m_tokens: CostPer1M
    avg_latency_ms: int
    strengths: list[str]
    weaknesses: list[str]
    max_context: int
    reasoning_score: int
    coding_score: int
    writing_score: int
    routable: bool


DEFAULT_METADATA: ModelMetadata = {
    "model_name": "Unknown Model",
    "provider": "groq",
    "cost_per_1m_tokens": {"input": 0.50, "output": 0.80},
    "avg_latency_ms": 800,
    "strengths": ["general purpose"],
    "weaknesses": ["metadata not curated"],
    "max_context": 8192,
    "reasoning_score": 55,
    "coding_score": 50,
    "writing_score": 55,
    "routable": False,
}

MODEL_REGISTRY: dict[str, ModelMetadata] = {
    "llama-3.1-8b-instant": {
        "model_name": "Llama 3.1 8B Instant",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.05, "output": 0.08},
        "avg_latency_ms": 650,
        "strengths": ["very fast", "very cheap", "simple Q&A", "classification", "prompt analysis"],
        "weaknesses": ["limited deep reasoning", "weaker for complex coding"],
        "max_context": 131072,
        "reasoning_score": 58,
        "coding_score": 60,
        "writing_score": 72,
        "routable": True,
    },
    "llama-3.3-70b-versatile": {
        "model_name": "Llama 3.3 70B Versatile",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.59, "output": 0.79},
        "avg_latency_ms": 1100,
        "strengths": ["high quality writing", "reports", "education", "general reasoning"],
        "weaknesses": ["slower and more expensive than smaller Groq models"],
        "max_context": 131072,
        "reasoning_score": 84,
        "coding_score": 78,
        "writing_score": 90,
        "routable": True,
    },
    "meta-llama/llama-4-scout-17b-16e-instruct": {
        "model_name": "Llama 4 Scout 17B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.11, "output": 0.34},
        "avg_latency_ms": 750,
        "strengths": ["efficient", "balanced", "long context", "general assistant tasks"],
        "weaknesses": ["not best for hardest coding or reasoning tasks"],
        "max_context": 131072,
        "reasoning_score": 80,
        "coding_score": 76,
        "writing_score": 84,
        "routable": True,
    },
    "qwen/qwen3-32b": {
        "model_name": "Qwen3 32B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.29, "output": 0.59},
        "avg_latency_ms": 950,
        "strengths": ["coding", "math", "structured reasoning", "multilingual"],
        "weaknesses": ["less polished for business writing"],
        "max_context": 131072,
        "reasoning_score": 88,
        "coding_score": 94,
        "writing_score": 78,
        "routable": True,
    },
    "openai/gpt-oss-20b": {
        "model_name": "GPT OSS 20B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.075, "output": 0.30},
        "avg_latency_ms": 600,
        "strengths": ["fast", "cheap", "balanced", "general tasks"],
        "weaknesses": ["should not dominate complex tasks"],
        "max_context": 131072,
        "reasoning_score": 70,
        "coding_score": 68,
        "writing_score": 72,
        "routable": True,
    },
    "openai/gpt-oss-120b": {
        "model_name": "GPT OSS 120B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.15, "output": 0.60},
        "avg_latency_ms": 1200,
        "strengths": ["deep reasoning", "complex analysis", "strong open-weight quality"],
        "weaknesses": ["higher latency than smaller Groq models"],
        "max_context": 131072,
        "reasoning_score": 91,
        "coding_score": 88,
        "writing_score": 86,
        "routable": True,
    },
    "gpt-4o-mini": {
        "model_name": "GPT-4o Mini",
        "provider": "openai",
        "cost_per_1m_tokens": {"input": 0.15, "output": 0.60},
        "avg_latency_ms": 1000,
        "strengths": ["balanced quality", "general Q&A", "classification", "cheap OpenAI tier"],
        "weaknesses": ["more expensive than Groq economy models"],
        "max_context": 128000,
        "reasoning_score": 82,
        "coding_score": 82,
        "writing_score": 84,
        "routable": True,
    },
    "gpt-4o": {
        "model_name": "GPT-4o",
        "provider": "openai",
        "cost_per_1m_tokens": {"input": 2.50, "output": 10.00},
        "avg_latency_ms": 1500,
        "strengths": ["premium quality", "multimodal", "complex reasoning", "coding", "writing"],
        "weaknesses": ["expensive"],
        "max_context": 128000,
        "reasoning_score": 94,
        "coding_score": 92,
        "writing_score": 94,
        "routable": True,
    },
    "o3-mini": {
        "model_name": "o3-mini",
        "provider": "openai",
        "cost_per_1m_tokens": {"input": 1.10, "output": 4.40},
        "avg_latency_ms": 1800,
        "strengths": ["deep reasoning", "math", "multi-step logic", "hard coding"],
        "weaknesses": ["slower", "not ideal for simple writing"],
        "max_context": 200000,
        "reasoning_score": 97,
        "coding_score": 91,
        "writing_score": 78,
        "routable": True,
    },
    "claude-3-5-sonnet": {
        "model_name": "Claude 3.5 Sonnet",
        "provider": "anthropic",
        "cost_per_1m_tokens": {"input": 3.00, "output": 15.00},
        "avg_latency_ms": 1600,
        "strengths": ["business writing", "RFPs", "long document analysis", "coding", "reasoning"],
        "weaknesses": ["premium cost"],
        "max_context": 200000,
        "reasoning_score": 92,
        "coding_score": 92,
        "writing_score": 96,
        "routable": True,
    },
    "claude-3-haiku": {
        "model_name": "Claude 3 Haiku",
        "provider": "anthropic",
        "cost_per_1m_tokens": {"input": 0.25, "output": 1.25},
        "avg_latency_ms": 850,
        "strengths": ["fast Anthropic tier", "simple tasks", "summaries", "classification"],
        "weaknesses": ["less capable than Sonnet"],
        "max_context": 200000,
        "reasoning_score": 73,
        "coding_score": 72,
        "writing_score": 80,
        "routable": True,
    },
    "whisper-large-v3": {
        "model_name": "Whisper Large V3",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.0, "output": 0.0},
        "avg_latency_ms": 0,
        "strengths": ["speech-to-text", "audio transcription"],
        "weaknesses": ["not a chat model"],
        "max_context": 0,
        "reasoning_score": 0,
        "coding_score": 0,
        "writing_score": 0,
        "routable": False,
    },
}


def is_allowlisted_model(model_id: str) -> bool:
    """True when model_id is in the deployment allowlist."""
    return model_id in MODEL_ALLOWLIST


def is_chat_model(model_id: str) -> bool:
    """True when model may be used for chat routing and Model Controls."""
    return model_id in CHAT_MODEL_IDS


def get_provider_for_model(model_id: str) -> str:
    """Return provider slug for a registry model id (defaults to groq)."""
    entry = MODEL_REGISTRY.get(model_id)
    if entry:
        return entry["provider"]
    return "groq"


def to_litellm_model(model_id: str) -> str:
    """Convert a registry model id to the LiteLLM model string."""
    provider = get_provider_for_model(model_id)
    litellm_id = LITELLM_MODEL_IDS.get(model_id, model_id)

    if provider == "groq":
        if litellm_id.startswith("groq/"):
            return litellm_id
        return f"groq/{litellm_id}"
    if provider == "openai":
        return litellm_id
    if provider == "anthropic":
        if litellm_id.startswith("anthropic/"):
            return litellm_id
        return f"anthropic/{litellm_id}"
    if provider == "google":
        if litellm_id.startswith("gemini/"):
            return litellm_id
        return f"gemini/{litellm_id}"
    return litellm_id


def get_registry_entry(model_id: str) -> ModelMetadata | None:
    """Return curated metadata for an allowlisted model id."""
    if not is_allowlisted_model(model_id):
        return None
    return MODEL_REGISTRY.get(model_id)


def get_all_registry_ids() -> list[str]:
    """All allowlisted model ids (chat + audio)."""
    return sorted(MODEL_ALLOWLIST)


def is_routable_model(model_id: str) -> bool:
    """True if model is allowlisted and marked routable for chat."""
    if not is_chat_model(model_id):
        return False
    entry = MODEL_REGISTRY.get(model_id)
    return bool(entry and entry["routable"])


def _guess_routable_from_id(model_id: str) -> bool:
    """Non-allowlisted models are never routable."""
    return is_routable_model(model_id)


def cost_per_1k_tokens(model_id: str, metadata: ModelMetadata | None = None) -> tuple[float, float]:
    """Convert per-1M registry rates to per-1K (uses DEFAULT for legacy history ids)."""
    meta = metadata or MODEL_REGISTRY.get(model_id) or DEFAULT_METADATA
    rates = meta["cost_per_1m_tokens"]
    return rates["input"] / 1000.0, rates["output"] / 1000.0


def tier_for_model(model_id: str, metadata: ModelMetadata | None = None) -> str:
    """Economy / standard / premium tier from blended cost."""
    meta = metadata or MODEL_REGISTRY.get(model_id) or DEFAULT_METADATA
    blended = meta["cost_per_1m_tokens"]["input"] + meta["cost_per_1m_tokens"]["output"]
    if blended <= 0.20:
        return "economy"
    if blended <= 1.20:
        return "standard"
    return "premium"
