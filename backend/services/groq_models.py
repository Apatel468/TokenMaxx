"""
Model catalog — sync allowlisted models with model_registry.py.

Groq-hosted models are optionally checked against the live Groq API.
OpenAI, Anthropic, and Google models are served from curated registry metadata.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from config.model_registry import (
    MODEL_ALLOWLIST,
    MODEL_REGISTRY,
    ModelMetadata,
    get_provider_for_model,
    get_registry_entry,
    is_allowlisted_model,
    is_routable_model,
)

logger = logging.getLogger(__name__)

GROQ_ENV_KEY = "GROQ_API_KEY"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"

_catalog_cache: list["GroqModelRecord"] | None = None


@dataclass
class GroqModelRecord:
    """One allowlisted model with registry metadata (all providers)."""

    model_id: str
    metadata: ModelMetadata
    in_registry: bool
    in_groq_api: bool

    @property
    def routable(self) -> bool:
        return self.metadata["routable"]

    @property
    def model_name(self) -> str:
        return self.metadata["model_name"]

    @property
    def provider(self) -> str:
        return self.metadata["provider"]


ModelCatalogRecord = GroqModelRecord


def _has_groq_key() -> bool:
    return bool(os.getenv(GROQ_ENV_KEY, "").strip())


def fetch_groq_api_model_ids() -> list[str]:
    """Query Groq for available model ids (Groq-hosted models only)."""
    if not _has_groq_key():
        logger.info(
            "Groq model sync skipped — %s not set; using allowlist catalog only.",
            GROQ_ENV_KEY,
        )
        return []

    api_key = os.getenv(GROQ_ENV_KEY, "").strip()
    request = urllib.request.Request(
        GROQ_MODELS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        logger.warning("Groq models API HTTP error %s — using allowlist only.", exc.code)
        return []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Groq models API failed (%s) — using allowlist only.", exc)
        return []

    data = payload.get("data", [])
    ids = [item["id"] for item in data if isinstance(item, dict) and item.get("id")]
    logger.info("Groq API returned %d models.", len(ids))
    return ids


def sync_groq_catalog(force: bool = False) -> list[GroqModelRecord]:
    """
    Build catalog from MODEL_ALLOWLIST.

    Groq API results set in_groq_api for Groq-hosted models only.
    """
    global _catalog_cache
    if _catalog_cache is not None and not force:
        return _catalog_cache

    api_ids = fetch_groq_api_model_ids()
    api_id_set = set(api_ids)

    groq_hosted = [
        mid for mid in MODEL_ALLOWLIST if get_provider_for_model(mid) == "groq"
    ]
    missing_from_api = [
        mid for mid in groq_hosted if api_ids and mid not in api_id_set
    ]
    for model_id in missing_from_api:
        entry = MODEL_REGISTRY[model_id]
        if entry["routable"]:
            logger.warning(
                "Allowlisted chat model '%s' not returned by Groq API — may be unavailable.",
                model_id,
            )
        else:
            logger.info(
                "Allowlisted audio model '%s' not in Groq API response.",
                model_id,
            )

    records: list[GroqModelRecord] = []
    for model_id in sorted(MODEL_ALLOWLIST):
        metadata = dict(MODEL_REGISTRY[model_id])
        is_groq_hosted = metadata["provider"] == "groq"
        records.append(
            GroqModelRecord(
                model_id=model_id,
                metadata=metadata,
                in_registry=True,
                in_groq_api=model_id in api_id_set if api_ids and is_groq_hosted else False,
            )
        )

    _catalog_cache = records
    routable_count = sum(1 for r in records if r.routable)
    logger.info(
        "Model catalog synced: %d allowlisted, %d routable for chat.",
        len(records),
        routable_count,
    )
    return records


def get_routable_models(force_sync: bool = False) -> list[GroqModelRecord]:
    """Return chat-routable allowlisted models only."""
    catalog = sync_groq_catalog(force=force_sync)
    return [record for record in catalog if record.routable]


def get_routable_model_ids(force_sync: bool = False) -> list[str]:
    """Ordered list of chat-routable model ids for routing and Model Controls."""
    return [record.model_id for record in get_routable_models(force_sync)]


def get_model_record(model_id: str) -> GroqModelRecord | None:
    """Look up a single allowlisted record from the cached catalog."""
    if not is_allowlisted_model(model_id):
        return None
    catalog = sync_groq_catalog()
    for record in catalog:
        if record.model_id == model_id:
            return record
    entry = get_registry_entry(model_id)
    if entry is None:
        return None
    return GroqModelRecord(
        model_id=model_id,
        metadata=dict(entry),
        in_registry=True,
        in_groq_api=False,
    )


def catalog_summary() -> dict[str, Any]:
    """Debug/admin summary of the allowlisted catalog."""
    catalog = sync_groq_catalog()
    groq_records = [r for r in catalog if r.metadata["provider"] == "groq"]
    api_checked = any(r.in_groq_api for r in groq_records)
    missing_from_api = (
        [r.model_id for r in groq_records if not r.in_groq_api and r.routable]
        if api_checked
        else []
    )

    return {
        "total": len(catalog),
        "routable": sum(1 for r in catalog if r.routable),
        "in_registry": len(catalog),
        "in_groq_api": sum(1 for r in groq_records if r.in_groq_api),
        "missing_from_registry": missing_from_api,
        "providers": sorted({r.metadata["provider"] for r in catalog}),
    }
