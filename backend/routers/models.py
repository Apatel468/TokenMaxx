"""
Models router — exposes Groq models from config/models.yaml.

GET /models returns each routed model with pricing from the YAML file.
"""

from fastapi import APIRouter

from models import ModelInfo
from services.config_loader import get_pricing, load_models_config

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelInfo])
def list_models() -> list[ModelInfo]:
    """Return all Groq models defined in models.yaml."""
    config = load_models_config()
    pricing = get_pricing()
    result = []

    # One entry per unique model string used in routing
    seen: set[str] = set()
    for task_type, route in config["models"].items():
        model_id = route["model"]
        if model_id in seen:
            continue
        seen.add(model_id)

        rates = pricing.get(model_id, {})
        result.append(
            ModelInfo(
                id=model_id,
                name=rates.get("label", model_id),
                provider="Groq",
                tier="economy" if "8b" in model_id else "standard",
                cost_per_1k_input=rates.get("input", 0.0),
                cost_per_1k_output=rates.get("output", 0.0),
                strengths=[task_type],
                avg_latency_ms=600 if "instant" in model_id else 900,
            )
        )

    return result
