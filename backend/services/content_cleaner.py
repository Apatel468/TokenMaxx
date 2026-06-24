"""
Content cleaner — normalize scraped page text for LLM context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_MAX_CONTENT_CHARS = 12_000
_BOILERPLATE_PATTERNS = (
    r"cookie(s)? (policy|preferences|settings)",
    r"accept all cookies",
    r"subscribe to our newsletter",
    r"sign up for (our )?newsletter",
    r"all rights reserved",
    r"privacy policy",
    r"terms of (service|use)",
    r"skip to (main )?content",
    r"enable javascript",
)


@dataclass
class CleanedContent:
    title: str
    content: str
    word_count: int


def clean_content(
    title: str,
    raw_text: str,
    *,
    max_chars: int = _MAX_CONTENT_CHARS,
) -> CleanedContent:
    """Remove boilerplate, collapse whitespace, and truncate oversized pages."""
    text = raw_text or ""
    text = _strip_boilerplate(text)
    text = _collapse_whitespace(text)
    text = _preserve_headings(text)

    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "\n\n[Content truncated]"

    clean_title = _collapse_whitespace(title or "").strip() or "Untitled"
    words = [w for w in text.split() if w]

    return CleanedContent(
        title=clean_title,
        content=text.strip(),
        word_count=len(words),
    )


def _strip_boilerplate(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    for line in lines:
        lower = line.lower().strip()
        if not lower:
            kept.append("")
            continue
        if any(re.search(pat, lower) for pat in _BOILERPLATE_PATTERNS):
            continue
        if len(lower) < 80 and lower.count("|") >= 3:
            continue
        kept.append(line)
    return "\n".join(kept)


def _collapse_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _preserve_headings(text: str) -> str:
    """Ensure markdown-style heading markers from scraper stay readable."""
    return re.sub(r"\n(#{1,3} .+)\n", r"\n\n\1\n\n", text)
