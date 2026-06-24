"""Tests for URL extraction and SSRF protection."""

import pytest

from services.url_security import (
    UnsafeUrlError,
    extract_urls,
    is_url_safe,
    normalize_url,
)


def test_extract_urls_from_prompt():
    urls = extract_urls(
        "Summarize https://openai.com/api/pricing and https://example.com/docs"
    )
    assert len(urls) == 2
    assert urls[0].startswith("https://openai.com")
    assert urls[1].startswith("https://example.com")


def test_extract_urls_max_five():
    text = " ".join(f"https://example.com/{i}" for i in range(10))
    urls = extract_urls(text, max_urls=5)
    assert len(urls) == 5


def test_blocks_localhost():
    assert not is_url_safe("http://localhost/page")
    assert not is_url_safe("http://127.0.0.1/admin")


def test_blocks_file_scheme():
    with pytest.raises(UnsafeUrlError):
        normalize_url("file:///etc/passwd")


def test_blocks_ftp_scheme():
    with pytest.raises(UnsafeUrlError):
        normalize_url("ftp://example.com/file")


def test_allows_public_https():
    url = normalize_url("https://example.com/path?q=1")
    assert url == "https://example.com/path?q=1"
