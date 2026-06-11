"""
Models router — exposes the catalog of AI models the router can choose from.

GET /models returns pricing, tiers, and strengths for each model.
Useful for the frontend to show users what models exist and why.
"""

from fastapi import APIRouter

from models import ModelInfo
from services.cost_tracker import MODEL_PRICING

router = APIRouter(prefix="/models", tags=["models"])

# Extra metadata not stored in MODEL_PRICING
_MODEL_METADATA: dict[str, dict] = {
    "gpt-4o": {
        "name": "GPT-4o",
        "provider": "OpenAI",
        "tier": "premium",
        "strengths": ["complex reasoning", "coding", "multimodal"],
        "avg_latency_ms": 2500,
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "provider": "OpenAI",
        "tier": "standard",
        "strengths": ["coding", "instruction following", "good value"],
        "avg_latency_ms": 1200,
    },
    "claude-3-haiku": {
        "name": "Claude 3 Haiku",
        "provider": "Anthropic",
        "tier": "economy",
        "strengths": ["summarization", "fast responses", "low cost"],
        "avg_latency_ms": 800,
    },
    "gemini-flash": {
        "name": "Gemini Flash",
        "provider": "Google",
        "tier": "economy",
        "strengths": ["Q&A", "translation", "very low cost"],
        "avg_latency_ms": 600,
    },
}


@router.get("", response_model=list[ModelInfo])
def list_models() -> list[ModelInfo]:
    """Return all models available to the router."""
    result = []
    for model_id, pricing in MODEL_PRICING.items():
        meta = _MODEL_METADATA[model_id]
        result.append(
            ModelInfo(
                id=model_id,
                name=meta["name"],
                provider=meta["provider"],
                tier=meta["tier"],
                cost_per_1k_input=pricing["input"],
                cost_per_1k_output=pricing["output"],
                strengths=meta["strengths"],
                avg_latency_ms=meta["avg_latency_ms"],
            )
        )
    return result
