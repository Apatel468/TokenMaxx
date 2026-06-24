"""
Web search — Tavily and Serper providers for live web research.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

DEFAULT_MAX_RESULTS = 5
_SEARCH_TIMEOUT = 20.0


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    score: float = 0.0


def search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> tuple[list[SearchResult], str]:
    """
    Search the web using the first configured provider (Tavily preferred).

    Returns (results, provider_name). Raises on total failure when no provider
    is configured; returns empty list when provider responds but finds nothing.
    """
    query = (query or "").strip()
    if not query:
        return [], ""

    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    serper_key = os.getenv("SERPER_API_KEY", "").strip()

    if tavily_key:
        try:
            return _search_tavily(query, tavily_key, max_results), "tavily"
        except Exception as exc:
            logger.warning("Tavily search failed: %s", exc)
            if serper_key:
                return _search_serper(query, serper_key, max_results), "serper"
            raise

    if serper_key:
        return _search_serper(query, serper_key, max_results), "serper"

    raise RuntimeError("No web search API key configured (TAVILY_API_KEY or SERPER_API_KEY)")


def has_search_provider() -> bool:
    return bool(
        os.getenv("TAVILY_API_KEY", "").strip()
        or os.getenv("SERPER_API_KEY", "").strip()
    )


def _search_tavily(query: str, api_key: str, max_results: int) -> list[SearchResult]:
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": False,
    }
    with httpx.Client(timeout=_SEARCH_TIMEOUT) as client:
        response = client.post("https://api.tavily.com/search", json=payload)
        response.raise_for_status()
        data = response.json()

    results: list[SearchResult] = []
    for item in data.get("results", [])[:max_results]:
        url = (item.get("url") or "").strip()
        if not url:
            continue
        results.append(
            SearchResult(
                title=(item.get("title") or "").strip(),
                url=url,
                snippet=(item.get("content") or item.get("snippet") or "").strip(),
                score=float(item.get("score") or 0.0),
            )
        )
    return results


def _search_serper(query: str, api_key: str, max_results: int) -> list[SearchResult]:
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": max_results}
    with httpx.Client(timeout=_SEARCH_TIMEOUT) as client:
        response = client.post(
            "https://google.serper.dev/search",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    results: list[SearchResult] = []
    for idx, item in enumerate(data.get("organic", [])[:max_results]):
        url = (item.get("link") or "").strip()
        if not url:
            continue
        results.append(
            SearchResult(
                title=(item.get("title") or "").strip(),
                url=url,
                snippet=(item.get("snippet") or "").strip(),
                score=max(1.0 - idx * 0.1, 0.1),
            )
        )
    return results
