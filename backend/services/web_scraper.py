"""
Web scraper — fetch and parse HTML pages for web research.

Uses httpx + BeautifulSoup (Python equivalent of fetch + Cheerio).
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup, Comment

from services.content_cleaner import CleanedContent, clean_content
from services.url_security import UnsafeUrlError, normalize_url

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = float(os.getenv("WEB_SCRAPE_TIMEOUT_SEC", "15"))
_MAX_PAGE_BYTES = int(os.getenv("WEB_SCRAPE_MAX_BYTES", str(2 * 1024 * 1024)))
_MAX_SCRAPE_DURATION = float(os.getenv("WEB_SCRAPE_MAX_DURATION_SEC", "45"))
_USER_AGENT = (
    "TokenMaxx-WebResearch/1.0 (+https://github.com/Apatel468/TokenMaxx)"
)

_REMOVE_TAGS = frozenset(
    {
        "script",
        "style",
        "noscript",
        "nav",
        "footer",
        "header",
        "aside",
        "iframe",
        "svg",
        "form",
        "button",
        "input",
        "select",
        "textarea",
        "meta",
        "link",
    }
)
_CONTENT_SELECTORS = (
    "article",
    "main",
    "[role='main']",
    "#content",
    ".content",
    "#main-content",
    ".main-content",
    "section",
)


@dataclass
class ScrapedPage:
    url: str
    title: str
    content: str
    word_count: int
    duration_ms: float
    error: str = ""


def scrape_url(url: str, *, timeout: float | None = None) -> ScrapedPage:
    """Download and extract readable content from a single URL."""
    start = time.perf_counter()
    safe_url = normalize_url(url)
    request_timeout = timeout or _DEFAULT_TIMEOUT

    try:
        html = _fetch_html(safe_url, request_timeout)
        title, raw_text = _extract_from_html(html)
        cleaned = clean_content(title, raw_text)
        duration_ms = (time.perf_counter() - start) * 1000
        return ScrapedPage(
            url=safe_url,
            title=cleaned.title,
            content=cleaned.content,
            word_count=cleaned.word_count,
            duration_ms=duration_ms,
        )
    except UnsafeUrlError as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        return ScrapedPage(
            url=url,
            title="",
            content="",
            word_count=0,
            duration_ms=duration_ms,
            error=str(exc),
        )
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.warning("Scrape failed for %s: %s", url, exc)
        return ScrapedPage(
            url=url,
            title="",
            content="",
            word_count=0,
            duration_ms=duration_ms,
            error="Unable to retrieve content from the source.",
        )


def scrape_urls(urls: list[str], *, max_pages: int = 5) -> list[ScrapedPage]:
    """Scrape up to max_pages URLs with a total duration cap."""
    deadline = time.perf_counter() + _MAX_SCRAPE_DURATION
    pages: list[ScrapedPage] = []
    for url in urls[:max_pages]:
        if time.perf_counter() >= deadline:
            break
        remaining = max(deadline - time.perf_counter(), 1.0)
        page_timeout = min(_DEFAULT_TIMEOUT, remaining)
        pages.append(scrape_url(url, timeout=page_timeout))
    return pages


def _fetch_html(url: str, timeout: float) -> str:
    headers = {"User-Agent": _USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        max_redirects=3,
    ) as client:
        with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            content_type = (response.headers.get("content-type") or "").lower()
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                raise ValueError(f"Unsupported content type: {content_type}")
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > _MAX_PAGE_BYTES:
                    raise ValueError("Page exceeds maximum allowed size")
                chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace")


def _extract_from_html(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(_REMOVE_TAGS):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    content_root = None
    for selector in _CONTENT_SELECTORS:
        content_root = soup.select_one(selector)
        if content_root and _text_length(content_root) > 120:
            break
        content_root = None

    if content_root is None:
        content_root = soup.body or soup

    lines: list[str] = []
    for element in content_root.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th"]):
        text = element.get_text(" ", strip=True)
        if not text or len(text) < 3:
            continue
        if element.name in ("h1", "h2", "h3"):
            level = int(element.name[1])
            lines.append(f"{'#' * level} {text}")
        else:
            lines.append(text)

    if not lines:
        fallback = content_root.get_text("\n", strip=True)
        lines = [ln for ln in fallback.splitlines() if ln.strip()]

    return title, "\n".join(lines)


def _text_length(node) -> int:
    return len(node.get_text(" ", strip=True))
