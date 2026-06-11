"""
Groq Models Service — sync live Groq API catalog with model_registry.py.

On each catalog read:
  1. GET https://api.groq.com/openai/v1/models (when GROQ_API_KEY is set)
  2. Merge API ids with registry metadata
  3. Log models present on Groq but missing from the registry (add them to model_registry.py)
  4. Log registry models not returned by the API (may be deprecated)

If no API key is available, falls back to registry routable models only.
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
    DEFAULT_METADATA,
    MODEL_REGISTRY,
    ModelMetadata,
    _guess_routable_from_id,
    get_registry_entry,
    is_routable_model,
)

logger = logging.getLogger(__name__)

GROQ_ENV_KEY = "GROQ_API_KEY"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"

# In-memory cache for one server process (refreshed on explicit sync or TTL expiry)
_catalog_cache: list["GroqModelRecord"] | None = None


@dataclass
class GroqModelRecord:
    """One Groq model merged from API + registry metadata."""

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


def _has_groq_key() -> bool:
    return bool(os.getenv(GROQ_ENV_KEY, "").strip())


def fetch_groq_api_model_ids() -> list[str]:
    """
    Query Groq for available model ids.

    Returns an empty list when the API key is missing or the request fails.
    """
    if not _has_groq_key():
        logger.info(
            "Groq model sync skipped — %s not set; using registry catalog only.",
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
        logger.warning("Groq models API HTTP error %s — using registry only.", exc.code)
        return []
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Groq models API failed (%s) — using registry only.", exc)
        return []

    data = payload.get("data", [])
    ids = [item["id"] for item in data if isinstance(item, dict) and item.get("id")]
    logger.info("Groq API returned %d models.", len(ids))
    return ids


def _build_metadata(model_id: str, in_registry: bool) -> ModelMetadata:
    """Return registry metadata or a safe default for unknown API models."""
    if in_registry:
        return dict(MODEL_REGISTRY[model_id])  # copy

    meta: ModelMetadata = {
        **DEFAULT_METADATA,
        "model_name": model_id,
        "routable": _guess_routable_from_id(model_id),
    }
    return meta


def sync_groq_catalog(force: bool = False) -> list[GroqModelRecord]:
    """
    Compare Groq API models against the registry and build the routable catalog.

    Set force=True to bypass the in-memory cache.
    """
    global _catalog_cache
    if _catalog_cache is not None and not force:
        return _catalog_cache

    api_ids = fetch_groq_api_model_ids()
    api_id_set = set(api_ids)

    # Union of API ids and registry ids so offline dev still sees the full registry.
    all_ids: list[str] = []
    seen: set[str] = set()
    for model_id in api_ids:
        if model_id not in seen:
            seen.add(model_id)
            all_ids.append(model_id)
    for model_id in MODEL_REGISTRY:
        if model_id not in seen:
            seen.add(model_id)
            all_ids.append(model_id)

    missing_from_registry = [mid for mid in api_ids if mid not in MODEL_REGISTRY]
    missing_from_api = [mid for mid in MODEL_REGISTRY if mid not in api_id_set and api_ids]

    for model_id in missing_from_registry:
        routable = _guess_routable_from_id(model_id)
        level = logger.warning if routable else logger.info
        level(
            "Groq model '%s' is NOT in model_registry.py — using defaults. "
            "Add curated metadata to backend/config/model_registry.py.",
            model_id,
        )

    for model_id in missing_from_api:
        entry = MODEL_REGISTRY[model_id]
        if entry["routable"]:
            logger.info(
                "Registry model '%s' not returned by Groq API — may be deprecated.",
                model_id,
            )

    records: list[GroqModelRecord] = []
    for model_id in all_ids:
        in_registry = model_id in MODEL_REGISTRY
        metadata = _build_metadata(model_id, in_registry)
        records.append(
            GroqModelRecord(
                model_id=model_id,
                metadata=metadata,
                in_registry=in_registry,
                in_groq_api=model_id in api_id_set,
            )
        )

    _catalog_cache = records
    routable_count = sum(1 for r in records if r.routable)
    logger.info(
        "Groq catalog synced: %d total, %d routable, %d missing from registry.",
        len(records),
        routable_count,
        len(missing_from_registry),
    )
    return records


def get_routable_models(force_sync: bool = False) -> list[GroqModelRecord]:
    """Return chat-routable models (API ∩ registry metadata, routable=True)."""
    catalog = sync_groq_catalog(force=force_sync)
    return [record for record in catalog if record.routable]


def get_routable_model_ids(force_sync: bool = False) -> list[str]:
    """Ordered list of routable Groq model ids for seeding SQLite settings."""
    return [record.model_id for record in get_routable_models(force_sync)]


def get_model_record(model_id: str) -> GroqModelRecord | None:
    """Look up a single merged record from the cached catalog."""
    catalog = sync_groq_catalog()
    for record in catalog:
        if record.model_id == model_id:
            return record
    entry = get_registry_entry(model_id)
    if entry is None and not _guess_routable_from_id(model_id):
        return None
    return GroqModelRecord(
        model_id=model_id,
        metadata=_build_metadata(model_id, entry is not None),
        in_registry=entry is not None,
        in_groq_api=False,
    )


def catalog_summary() -> dict[str, Any]:
    """Debug/admin summary of the last catalog sync."""
    catalog = sync_groq_catalog()
    return {
        "total": len(catalog),
        "routable": sum(1 for r in catalog if r.routable),
        "in_registry": sum(1 for r in catalog if r.in_registry),
        "in_groq_api": sum(1 for r in catalog if r.in_groq_api),
        "missing_from_registry": [
            r.model_id for r in catalog if not r.in_registry and r.in_groq_api
        ],
    }
