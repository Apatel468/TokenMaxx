"""
Web research service — search, scrape, and inject live web content into chat.

Follows the same pattern as rag_service.py.

When a user-supplied URL is bot-protected, falls back to web search for
alternate sources (scrape alternates, then search snippets if needed).
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import urlparse

from services.context_builder import PromptContext
from services.url_security import extract_urls, is_url_safe, normalize_url
from services.web_scraper import ScrapedPage, scrape_urls
from services.web_search import SearchResult, has_search_provider, search

logger = logging.getLogger(__name__)

_WEB_RESEARCH_INSTRUCTIONS = (
    "You are answering using supplied web content. Cite sources when possible. "
    "Do not invent facts not present in the supplied material."
)

_FALLBACK_NOTE = (
    "Note: The user's original link could not be accessed (likely bot protection). "
    "Alternate web sources below were used instead. Mention this briefly if relevant."
)

_SNIPPET_ONLY_NOTE = (
    "Note: Full page scraping was unavailable. Search excerpts below were used. "
    "Treat them as partial context and avoid overstating certainty."
)

_WEB_RESEARCH_KEYWORDS = (
    "latest",
    "current",
    "recent",
    "news",
    "pricing",
    "price",
    "cost per",
    "today",
    "announcement",
    "competitor",
    "market research",
    "company research",
    "enterprise plan",
    "release notes",
    "what is the current",
    "right now",
    "as of",
    "documentation",
    "docs",
    "compare",
    "versus",
    "vs ",
)

_RATE_LIMIT_WINDOW_SEC = 60
_RATE_LIMIT_MAX_REQUESTS = 10
_rate_buckets: dict[int, list[float]] = defaultdict(list)


@dataclass
class WebSource:
    url: str
    title: str
    snippet: str = ""
    word_count: int = 0


@dataclass
class WebResearchResult:
    web_research_used: bool = False
    search_query: str = ""
    search_provider: str = ""
    sources: list[WebSource] = field(default_factory=list)
    context_block: str = ""
    scrape_duration_ms: float = 0.0
    error_message: str = ""
    direct_urls: bool = False
    fallback_used: bool = False
    fallback_reason: str = ""
    original_blocked_urls: list[str] = field(default_factory=list)


def should_use_web_research(prompt: str, task_type: str) -> bool:
    """True when the prompt needs live web data."""
    text = (prompt or "").strip()
    if not text:
        return False
    if task_type == "web_research":
        return True
    if extract_urls(text):
        return True
    lower = text.lower()
    return any(kw in lower for kw in _WEB_RESEARCH_KEYWORDS)


def check_rate_limit(user_id: int) -> bool:
    """Return True if the user is within the web research rate limit."""
    now = time.time()
    bucket = _rate_buckets[user_id]
    _rate_buckets[user_id] = [t for t in bucket if now - t < _RATE_LIMIT_WINDOW_SEC]
    if len(_rate_buckets[user_id]) >= _RATE_LIMIT_MAX_REQUESTS:
        return False
    _rate_buckets[user_id].append(now)
    return True


def retrieve_web_for_chat(
    user_id: int,
    prompt: str,
    task_type: str,
    *,
    max_results: int = 5,
) -> WebResearchResult:
    """
    Search and/or scrape web pages for chat context.

    Direct URLs are scraped first; on failure, search finds alternate sources.
    """
    if not should_use_web_research(prompt, task_type):
        return WebResearchResult()

    if not check_rate_limit(user_id):
        return WebResearchResult(
            error_message="Web research rate limit exceeded. Please try again shortly.",
        )

    direct_urls = extract_urls(prompt, max_urls=5)
    start = time.perf_counter()

    if direct_urls:
        result = _scrape_and_build(
            prompt=prompt,
            urls=direct_urls,
            search_query="",
            search_provider="direct",
            direct_urls=True,
            snippets={},
            start=start,
        )
        if result.web_research_used:
            return result
        if has_search_provider():
            logger.info(
                "Direct URL scrape failed for user %s — trying search fallback",
                user_id,
            )
            fallback = _search_fallback_after_blocked(
                prompt=prompt,
                blocked_urls=direct_urls,
                start=start,
                max_results=max_results,
            )
            if fallback.web_research_used:
                return fallback
            if fallback.error_message:
                result.error_message = fallback.error_message
            return result
        return result

    if not has_search_provider():
        return WebResearchResult(
            error_message="Unable to retrieve web search results.",
        )

    return _run_search_pipeline(
        user_id=user_id,
        prompt=prompt,
        search_query=_build_search_query(prompt),
        start=start,
        max_results=max_results,
        blocked_domains=set(),
    )


def apply_web_research_to_context(
    context: PromptContext,
    web: WebResearchResult,
) -> PromptContext:
    """Append web research content to the system prompt."""
    context.web_search_query = web.search_query
    context.web_search_provider = web.search_provider
    context.web_scrape_duration_ms = web.scrape_duration_ms
    context.web_sources = list(web.sources)
    context.web_research_direct_urls = web.direct_urls
    context.web_fallback_used = web.fallback_used
    context.web_fallback_reason = web.fallback_reason
    context.web_original_blocked_urls = list(web.original_blocked_urls)

    if web.error_message and not web.context_block:
        context.web_research_error = web.error_message
        return context

    if not web.web_research_used or not web.context_block:
        return context

    block = f"{_WEB_RESEARCH_INSTRUCTIONS}\n\n{web.context_block}"
    if context.system_prompt:
        context.system_prompt = f"{context.system_prompt.strip()}\n\n{block}"
    else:
        context.system_prompt = block

    context.web_research_used = True
    extra_chars = len(block)
    context.estimated_input_tokens += max(extra_chars // 4, 0)
    return context


def web_research_metadata_dict(context: PromptContext) -> dict:
    """API-friendly web research fields."""
    sources = [
        {
            "url": s.url,
            "title": s.title,
            "snippet": s.snippet,
            "word_count": s.word_count,
        }
        for s in (context.web_sources or [])
    ]
    return {
        "web_research_used": bool(context.web_research_used),
        "web_search_query": context.web_search_query or "",
        "web_search_provider": context.web_search_provider or "",
        "web_scrape_duration_ms": context.web_scrape_duration_ms or 0.0,
        "web_source_count": len(sources),
        "web_sources": sources,
        "web_research_error": context.web_research_error or "",
        "web_research_direct_urls": bool(context.web_research_direct_urls),
        "web_fallback_used": bool(getattr(context, "web_fallback_used", False)),
        "web_fallback_reason": getattr(context, "web_fallback_reason", "") or "",
        "web_original_blocked_urls": list(
            getattr(context, "web_original_blocked_urls", []) or []
        ),
    }


def serialize_web_sources(sources: list[WebSource]) -> str | None:
    if not sources:
        return None
    payload = [
        {
            "url": s.url,
            "title": s.title,
            "snippet": s.snippet,
            "word_count": s.word_count,
        }
        for s in sources
    ]
    return json.dumps(payload)


def deserialize_web_sources(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _search_fallback_after_blocked(
    *,
    prompt: str,
    blocked_urls: list[str],
    start: float,
    max_results: int,
) -> WebResearchResult:
    """Search for alternate sources when user-supplied URLs cannot be scraped."""
    search_query = _build_fallback_search_query(prompt, blocked_urls)
    blocked_domains = {_domain_from_url(u) for u in blocked_urls}
    blocked_domains.discard("")

    return _run_search_pipeline(
        user_id=0,
        prompt=prompt,
        search_query=search_query,
        start=start,
        max_results=max_results,
        blocked_domains=blocked_domains,
        fallback_used=True,
        fallback_reason="direct_scrape_blocked",
        original_blocked_urls=blocked_urls,
    )


def _run_search_pipeline(
    *,
    user_id: int,
    prompt: str,
    search_query: str,
    start: float,
    max_results: int,
    blocked_domains: set[str],
    fallback_used: bool = False,
    fallback_reason: str = "",
    original_blocked_urls: list[str] | None = None,
) -> WebResearchResult:
    try:
        results, provider = search(search_query, max_results=max_results)
    except Exception as exc:
        logger.warning("Web search failed for user %s: %s", user_id, exc)
        return WebResearchResult(
            search_query=search_query,
            error_message="Unable to retrieve web search results.",
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            original_blocked_urls=original_blocked_urls or [],
        )

    if not results:
        return WebResearchResult(
            search_query=search_query,
            search_provider=provider,
            error_message="No relevant content could be extracted.",
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            original_blocked_urls=original_blocked_urls or [],
        )

    urls: list[str] = []
    snippets: dict[str, str] = {}
    filtered_results: list[SearchResult] = []

    for hit in results:
        domain = _domain_from_url(hit.url)
        if domain in blocked_domains:
            continue
        if not is_url_safe(hit.url):
            continue
        try:
            safe = normalize_url(hit.url)
        except Exception:
            continue
        if safe in urls:
            continue
        urls.append(safe)
        snippets[safe] = hit.snippet
        filtered_results.append(hit)
        if len(urls) >= max_results:
            break

    if not urls and not filtered_results:
        return WebResearchResult(
            search_query=search_query,
            search_provider=provider,
            error_message="No relevant content could be extracted.",
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            original_blocked_urls=original_blocked_urls or [],
        )

    if urls:
        scrape_result = _scrape_and_build(
            prompt=prompt,
            urls=urls,
            search_query=search_query,
            search_provider=provider,
            direct_urls=False,
            snippets=snippets,
            start=start,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            original_blocked_urls=original_blocked_urls or [],
            intro_note=_FALLBACK_NOTE if fallback_used else "",
        )
        if scrape_result.web_research_used:
            return scrape_result

    # Last resort: inject search snippets without full page scrape
    snippet_result = _build_from_search_snippets(
        results=filtered_results or results,
        search_query=search_query,
        search_provider=provider,
        start=start,
        fallback_used=True,
        fallback_reason=fallback_reason or "scrape_failed_snippets_used",
        original_blocked_urls=original_blocked_urls or [],
        intro_note=_FALLBACK_NOTE if fallback_used else _SNIPPET_ONLY_NOTE,
    )
    if snippet_result.web_research_used:
        return snippet_result

    return WebResearchResult(
        search_query=search_query,
        search_provider=provider,
        scrape_duration_ms=(time.perf_counter() - start) * 1000,
        error_message="No relevant content could be extracted.",
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        original_blocked_urls=original_blocked_urls or [],
    )


def _scrape_and_build(
    *,
    prompt: str,
    urls: list[str],
    search_query: str,
    search_provider: str,
    direct_urls: bool,
    snippets: dict[str, str],
    start: float,
    fallback_used: bool = False,
    fallback_reason: str = "",
    original_blocked_urls: list[str] | None = None,
    intro_note: str = "",
) -> WebResearchResult:
    pages = scrape_urls(urls, max_pages=5)
    scrape_duration_ms = (time.perf_counter() - start) * 1000

    sources: list[WebSource] = []
    content_sections: list[str] = []

    for page in pages:
        if page.error or not page.content.strip():
            continue
        snippet = snippets.get(page.url, "")
        sources.append(
            WebSource(
                url=page.url,
                title=page.title or page.url,
                snippet=snippet,
                word_count=page.word_count,
            )
        )
        content_sections.append(
            f"### Source: {page.title or page.url}\nURL: {page.url}\n\n{page.content}"
        )

    if not content_sections:
        failed = any(p.error for p in pages)
        msg = (
            "Unable to retrieve content from the source."
            if failed
            else "No relevant content could be extracted."
        )
        return WebResearchResult(
            search_query=search_query,
            search_provider=search_provider,
            scrape_duration_ms=scrape_duration_ms,
            error_message=msg,
            direct_urls=direct_urls,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            original_blocked_urls=original_blocked_urls or [],
        )

    prefix = f"{intro_note}\n\n" if intro_note else ""
    context_block = prefix + "Web research content:\n\n" + "\n\n---\n\n".join(
        content_sections
    )
    return WebResearchResult(
        web_research_used=True,
        search_query=search_query or _build_search_query(prompt),
        search_provider=search_provider,
        sources=sources,
        context_block=context_block,
        scrape_duration_ms=scrape_duration_ms,
        direct_urls=direct_urls,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        original_blocked_urls=original_blocked_urls or [],
    )


def _build_from_search_snippets(
    *,
    results: list[SearchResult],
    search_query: str,
    search_provider: str,
    start: float,
    fallback_used: bool,
    fallback_reason: str,
    original_blocked_urls: list[str],
    intro_note: str,
) -> WebResearchResult:
    sources: list[WebSource] = []
    content_sections: list[str] = []

    for hit in results:
        text = (hit.snippet or "").strip()
        if not text:
            continue
        sources.append(
            WebSource(
                url=hit.url,
                title=hit.title or hit.url,
                snippet=text,
                word_count=len(text.split()),
            )
        )
        content_sections.append(
            f"### Source: {hit.title or hit.url}\nURL: {hit.url}\n\n{text}"
        )

    if not content_sections:
        return WebResearchResult(
            search_query=search_query,
            search_provider=search_provider,
            scrape_duration_ms=(time.perf_counter() - start) * 1000,
            error_message="No relevant content could be extracted.",
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            original_blocked_urls=original_blocked_urls,
        )

    prefix = f"{intro_note}\n\n" if intro_note else ""
    context_block = prefix + "Web research content (search excerpts):\n\n" + "\n\n---\n\n".join(
        content_sections
    )
    return WebResearchResult(
        web_research_used=True,
        search_query=search_query,
        search_provider=search_provider,
        sources=sources,
        context_block=context_block,
        scrape_duration_ms=(time.perf_counter() - start) * 1000,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        original_blocked_urls=original_blocked_urls,
    )


def _build_search_query(prompt: str) -> str:
    """Strip URLs and collapse whitespace for a cleaner search query."""
    text = re.sub(r"https?://\S+", "", prompt or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500] if text else (prompt or "").strip()[:500]


def _build_fallback_search_query(prompt: str, failed_urls: list[str]) -> str:
    """Combine URL-derived product hints with the user's question."""
    hints = _hints_from_urls(failed_urls)
    text_part = _build_search_query(prompt)
    parts = [p for p in (hints, text_part) if p]
    return " ".join(parts)[:500]


def _hints_from_urls(urls: list[str]) -> str:
    """Extract readable product/page hints from URL paths."""
    hints: list[str] = []
    for url in urls:
        path = urlparse(url).path.rstrip("/")
        if not path:
            continue
        segment = path.split("/")[-1]
        segment = re.sub(r"-p\d+.*$", "", segment, flags=re.IGNORECASE)
        segment = re.sub(r"\?.*$", "", segment)
        readable = segment.replace("-", " ").replace("_", " ").strip()
        if readable and readable not in hints:
            hints.append(readable)
    return " ".join(hints)


def _domain_from_url(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""
