"""
Models router — exposes the Groq model catalog from model_registry.py.

GET /models        → all routable models with metadata
GET /models/sync   → refresh Groq API catalog and return sync summary
"""

from fastapi import APIRouter

from config.model_registry import cost_per_1k_tokens, tier_for_model
from models import ModelInfo, ModelSyncSummary
from services.groq_models import catalog_summary, get_routable_models, sync_groq_catalog

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelInfo])
def list_models() -> list[ModelInfo]:
    """Return all routable Groq models with registry metadata."""
    result: list[ModelInfo] = []
    for record in get_routable_models():
        meta = record.metadata
        cost_in, cost_out = cost_per_1k_tokens(record.model_id, meta)
        result.append(
            ModelInfo(
                id=record.model_id,
                name=meta["model_name"],
                provider=meta["provider"],
                tier=tier_for_model(record.model_id, meta),
                cost_per_1k_input=cost_in,
                cost_per_1k_output=cost_out,
                strengths=meta["strengths"],
                avg_latency_ms=meta["avg_latency_ms"],
            )
        )
    return result


@router.get("/sync", response_model=ModelSyncSummary)
def sync_models() -> ModelSyncSummary:
    """Force-refresh the Groq API catalog and report registry gaps."""
    sync_groq_catalog(force=True)
    summary = catalog_summary()
    return ModelSyncSummary(**summary)
