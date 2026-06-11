"""
Model Registry — static metadata for Groq models used by the TokenMaxx router.

HOW TO ADD A NEW GROQ MODEL (no router code changes):
  1. Add an entry below keyed by the exact Groq model id (from GET /openai/v1/models).
  2. Set routable=True for chat-completion models; False for audio/guard/embedding models.
  3. Fill scores (0–100), cost_per_1m_tokens, avg_latency_ms, max_context, strengths/weaknesses.
  4. Restart the backend — groq_models.py will pick it up on the next catalog sync.
  5. Users can enable/disable it in Model Controls (SQLite seeds new ids automatically).

The scoring router (model_scorer.py) reads ONLY this registry + live Groq API list.
It never hardcodes model ids — task routing is computed from metadata scores.
"""

from __future__ import annotations

from typing import TypedDict


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


# Default metadata applied to API models missing from the registry (logged as warnings).
DEFAULT_METADATA: ModelMetadata = {
    "model_name": "Unknown Groq Model",
    "provider": "groq",
    "cost_per_1m_tokens": {"input": 0.50, "output": 0.80},
    "avg_latency_ms": 800,
    "strengths": ["general purpose"],
    "weaknesses": ["metadata not curated — add to model_registry.py"],
    "max_context": 8192,
    "reasoning_score": 55,
    "coding_score": 50,
    "writing_score": 55,
    "routable": True,
}

# ---------------------------------------------------------------------------
# Curated Groq chat-model catalog
# Keys MUST match Groq API model ids exactly.
# ---------------------------------------------------------------------------

MODEL_REGISTRY: dict[str, ModelMetadata] = {
    # --- Economy / fast ---
    "llama-3.1-8b-instant": {
        "model_name": "Llama 3.1 8B Instant",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.05, "output": 0.08},
        "avg_latency_ms": 700,
        "strengths": ["very fast", "cheap", "simple Q&A", "classification"],
        "weaknesses": ["limited reasoning depth", "shorter complex outputs"],
        "max_context": 131072,
        "reasoning_score": 60,
        "coding_score": 65,
        "writing_score": 80,
        "routable": True,
    },
    "llama-3.2-1b-preview": {
        "model_name": "Llama 3.2 1B Preview",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.04, "output": 0.06},
        "avg_latency_ms": 500,
        "strengths": ["ultra fast", "minimal cost"],
        "weaknesses": ["low capability ceiling"],
        "max_context": 8192,
        "reasoning_score": 45,
        "coding_score": 40,
        "writing_score": 50,
        "routable": True,
    },
    "llama-3.2-3b-preview": {
        "model_name": "Llama 3.2 3B Preview",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.06, "output": 0.08},
        "avg_latency_ms": 550,
        "strengths": ["fast", "lightweight"],
        "weaknesses": ["moderate reasoning"],
        "max_context": 8192,
        "reasoning_score": 52,
        "coding_score": 50,
        "writing_score": 58,
        "routable": True,
    },
    "openai/gpt-oss-20b": {
        "model_name": "GPT OSS 20B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.075, "output": 0.30},
        "avg_latency_ms": 600,
        "strengths": ["fast open-weight", "balanced"],
        "weaknesses": ["newer model — less battle-tested"],
        "max_context": 131072,
        "reasoning_score": 72,
        "coding_score": 70,
        "writing_score": 75,
        "routable": True,
    },
    # --- Standard ---
    "llama-3.1-70b-versatile": {
        "model_name": "Llama 3.1 70B Versatile",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.59, "output": 0.79},
        "avg_latency_ms": 900,
        "strengths": ["strong generalist", "long context"],
        "weaknesses": ["higher cost than 8B"],
        "max_context": 131072,
        "reasoning_score": 78,
        "coding_score": 75,
        "writing_score": 82,
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
    "mixtral-8x7b-32768": {
        "model_name": "Mixtral 8x7B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.24, "output": 0.24},
        "avg_latency_ms": 800,
        "strengths": ["MoE efficiency", "multilingual"],
        "weaknesses": ["older architecture vs Llama 3.3"],
        "max_context": 32768,
        "reasoning_score": 75,
        "coding_score": 72,
        "writing_score": 76,
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
    "meta-llama/llama-4-maverick-17b-128e-instruct": {
        "model_name": "Llama 4 Maverick 17B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.20, "output": 0.60},
        "avg_latency_ms": 900,
        "strengths": ["large MoE capacity", "complex tasks"],
        "weaknesses": ["higher cost"],
        "max_context": 131072,
        "reasoning_score": 86,
        "coding_score": 82,
        "writing_score": 86,
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
    "deepseek-r1-distill-llama-70b": {
        "model_name": "DeepSeek R1 Distill Llama 70B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.59, "output": 0.79},
        "avg_latency_ms": 1200,
        "strengths": ["chain-of-thought reasoning", "math"],
        "weaknesses": ["slower", "verbose reasoning traces"],
        "max_context": 131072,
        "reasoning_score": 92,
        "coding_score": 85,
        "writing_score": 80,
        "routable": True,
    },
    "deepseek-r1-distill-qwen-32b": {
        "model_name": "DeepSeek R1 Distill Qwen 32B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.29, "output": 0.59},
        "avg_latency_ms": 1100,
        "strengths": ["reasoning + coding blend"],
        "weaknesses": ["reasoning verbosity"],
        "max_context": 131072,
        "reasoning_score": 90,
        "coding_score": 90,
        "writing_score": 78,
        "routable": True,
    },
    "llama3-groq-8b-8192-tool-use-preview": {
        "model_name": "Llama 3 Groq 8B Tool Use",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.05, "output": 0.08},
        "avg_latency_ms": 700,
        "strengths": ["tool calling", "agents"],
        "weaknesses": ["preview status"],
        "max_context": 8192,
        "reasoning_score": 65,
        "coding_score": 72,
        "writing_score": 70,
        "routable": True,
    },
    "llama3-groq-70b-8192-tool-use-preview": {
        "model_name": "Llama 3 Groq 70B Tool Use",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.59, "output": 0.79},
        "avg_latency_ms": 950,
        "strengths": ["tool calling at scale"],
        "weaknesses": ["preview status", "8k context"],
        "max_context": 8192,
        "reasoning_score": 80,
        "coding_score": 78,
        "writing_score": 78,
        "routable": True,
    },
    # --- Legacy (may still appear on some Groq accounts) ---
    "llama3-8b-8192": {
        "model_name": "Llama 3 8B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.05, "output": 0.08},
        "avg_latency_ms": 750,
        "strengths": ["legacy fast model"],
        "weaknesses": ["deprecated — prefer llama-3.1-8b-instant"],
        "max_context": 8192,
        "reasoning_score": 58,
        "coding_score": 60,
        "writing_score": 72,
        "routable": True,
    },
    "llama3-70b-8192": {
        "model_name": "Llama 3 70B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.59, "output": 0.79},
        "avg_latency_ms": 950,
        "strengths": ["legacy 70B"],
        "weaknesses": ["deprecated — prefer llama-3.3-70b-versatile"],
        "max_context": 8192,
        "reasoning_score": 76,
        "coding_score": 74,
        "writing_score": 80,
        "routable": True,
    },
    # --- Non-routable (audio, safety, embeddings) — listed for API sync logging ---
    "whisper-large-v3": {
        "model_name": "Whisper Large V3",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.0, "output": 0.0},
        "avg_latency_ms": 0,
        "strengths": ["speech-to-text"],
        "weaknesses": ["not a chat model"],
        "max_context": 0,
        "reasoning_score": 0,
        "coding_score": 0,
        "writing_score": 0,
        "routable": False,
    },
    "whisper-large-v3-turbo": {
        "model_name": "Whisper Large V3 Turbo",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.0, "output": 0.0},
        "avg_latency_ms": 0,
        "strengths": ["fast speech-to-text"],
        "weaknesses": ["not a chat model"],
        "max_context": 0,
        "reasoning_score": 0,
        "coding_score": 0,
        "writing_score": 0,
        "routable": False,
    },
    "llama-guard-3-8b": {
        "model_name": "Llama Guard 3 8B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.05, "output": 0.05},
        "avg_latency_ms": 400,
        "strengths": ["content moderation"],
        "weaknesses": ["not for chat responses"],
        "max_context": 8192,
        "reasoning_score": 0,
        "coding_score": 0,
        "writing_score": 0,
        "routable": False,
    },
    "meta-llama/llama-guard-4-12b": {
        "model_name": "Llama Guard 4 12B",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.05, "output": 0.05},
        "avg_latency_ms": 500,
        "strengths": ["safety classification"],
        "weaknesses": ["not for chat responses"],
        "max_context": 8192,
        "reasoning_score": 0,
        "coding_score": 0,
        "writing_score": 0,
        "routable": False,
    },
    "meta-llama/llama-prompt-guard-2-22m": {
        "model_name": "Llama Prompt Guard 2 22M",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.03, "output": 0.03},
        "avg_latency_ms": 200,
        "strengths": ["prompt injection detection"],
        "weaknesses": ["not for chat responses"],
        "max_context": 512,
        "reasoning_score": 0,
        "coding_score": 0,
        "writing_score": 0,
        "routable": False,
    },
    "meta-llama/llama-prompt-guard-2-86m": {
        "model_name": "Llama Prompt Guard 2 86M",
        "provider": "groq",
        "cost_per_1m_tokens": {"input": 0.04, "output": 0.04},
        "avg_latency_ms": 250,
        "strengths": ["prompt injection detection"],
        "weaknesses": ["not for chat responses"],
        "max_context": 512,
        "reasoning_score": 0,
        "coding_score": 0,
        "writing_score": 0,
        "routable": False,
    },
}


def get_registry_entry(model_id: str) -> ModelMetadata | None:
    """Return curated metadata for a model id, or None if not in registry."""
    return MODEL_REGISTRY.get(model_id)


def get_all_registry_ids() -> list[str]:
    """All model ids defined in the registry (routable and non-routable)."""
    return list(MODEL_REGISTRY.keys())


def is_routable_model(model_id: str) -> bool:
    """True if registry marks this model as chat-routable."""
    entry = MODEL_REGISTRY.get(model_id)
    if entry is not None:
        return entry["routable"]
    return _guess_routable_from_id(model_id)


def _guess_routable_from_id(model_id: str) -> bool:
    """Heuristic for API-only models not yet in the registry."""
    lowered = model_id.lower()
    skip_tokens = (
        "whisper",
        "guard",
        "embed",
        "tts",
        "playai",
        "orpheus",
        "safeguard",
    )
    return not any(token in lowered for token in skip_tokens)


def cost_per_1k_tokens(model_id: str, metadata: ModelMetadata | None = None) -> tuple[float, float]:
    """Convert per-1M registry rates to per-1K for cost_tracker compatibility."""
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
