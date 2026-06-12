"""
Model Registry — curated metadata for Groq models allowed in TokenMaxx.

Only models in GROQ_MODEL_ALLOWLIST are synced, routed, or shown in Model Controls.
Chat routing uses GROQ_CHAT_MODEL_IDS (excludes whisper-large-v3).
"""

from __future__ import annotations

from typing import TypedDict

# ---------------------------------------------------------------------------
# Groq allowlist — sole source of model ids for this deployment
# ---------------------------------------------------------------------------

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

# Chat-completion models eligible for routing / Model Controls toggles
GROQ_CHAT_MODEL_IDS: frozenset[str] = frozenset(
    GROQ_MODEL_ALLOWLIST - {"whisper-large-v3"}
)

# Speech/audio only — never used for normal chat routing
GROQ_AUDIO_MODEL_IDS: frozenset[str] = frozenset({"whisper-large-v3"})


class CostPer1M(TypedDict):
    input: float
    output: float


class ModelMetadata(TypedDict):
    model_name: str
    provider: str
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
    "model_name": "Unknown Groq Model",
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
        "avg_latency_ms": 700,
        "strengths": ["very fast", "cheap", "simple Q&A", "classification"],
        "weaknesses": ["limited reasoning depth"],
        "max_context": 131072,
        "reasoning_score": 60,
        "coding_score": 65,
        "writing_score": 80,
        "routable": True,
    },
    "llama-3.3-70b-versatile": {
        "model_name": "Llama 3.3 70B Versatile",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.59, "output": 0.79},
        "avg_latency_ms": 850,
        "strengths": ["high quality writing", "reports", "education"],
        "weaknesses": ["slower than 8B instant"],
        "max_context": 131072,
        "reasoning_score": 82,
        "coding_score": 78,
        "writing_score": 88,
        "routable": True,
    },
    "meta-llama/llama-4-scout-17b-16e-instruct": {
        "model_name": "Llama 4 Scout 17B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.11, "output": 0.34},
        "avg_latency_ms": 750,
        "strengths": ["next-gen Llama", "efficient MoE"],
        "weaknesses": ["smaller than 70B variants"],
        "max_context": 131072,
        "reasoning_score": 80,
        "coding_score": 78,
        "writing_score": 84,
        "routable": True,
    },
    "qwen/qwen3-32b": {
        "model_name": "Qwen3 32B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.29, "output": 0.59},
        "avg_latency_ms": 950,
        "strengths": ["coding", "math", "structured reasoning"],
        "weaknesses": ["may emit chain-of-thought unless suppressed"],
        "max_context": 131072,
        "reasoning_score": 85,
        "coding_score": 92,
        "writing_score": 78,
        "routable": True,
    },
    "openai/gpt-oss-20b": {
        "model_name": "GPT OSS 20B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.075, "output": 0.30},
        "avg_latency_ms": 600,
        "strengths": ["fast open-weight", "balanced"],
        "weaknesses": ["smaller than 120B variant"],
        "max_context": 131072,
        "reasoning_score": 72,
        "coding_score": 70,
        "writing_score": 75,
        "routable": True,
    },
    "openai/gpt-oss-120b": {
        "model_name": "GPT OSS 120B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.15, "output": 0.60},
        "avg_latency_ms": 1100,
        "strengths": ["frontier open-weight", "deep reasoning"],
        "weaknesses": ["highest latency in tier"],
        "max_context": 131072,
        "reasoning_score": 90,
        "coding_score": 88,
        "writing_score": 87,
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
    """True when model_id is in the Groq deployment allowlist."""
    return model_id in GROQ_MODEL_ALLOWLIST


def is_chat_model(model_id: str) -> bool:
    """True when model may be used for chat routing and Model Controls."""
    return model_id in GROQ_CHAT_MODEL_IDS


def get_registry_entry(model_id: str) -> ModelMetadata | None:
    """Return curated metadata for an allowlisted model id."""
    if not is_allowlisted_model(model_id):
        return None
    return MODEL_REGISTRY.get(model_id)


def get_all_registry_ids() -> list[str]:
    """All allowlisted model ids (chat + audio)."""
    return sorted(GROQ_MODEL_ALLOWLIST)


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
