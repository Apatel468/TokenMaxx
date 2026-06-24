"""
URL security — SSRF protection and URL extraction for web research.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

_BLOCKED_SCHEMES = frozenset({"file", "ftp", "gopher", "data", "javascript", "blob"})
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\"')\]]+",
    re.IGNORECASE,
)


class UnsafeUrlError(ValueError):
    """Raised when a URL fails SSRF safety checks."""


def extract_urls(text: str, *, max_urls: int = 5) -> list[str]:
    """Extract up to max_urls http(s) URLs from free-form text."""
    if not text:
        return []
    seen: set[str] = set()
    urls: list[str] = []
    for match in _URL_PATTERN.finditer(text):
        raw = match.group(0).rstrip(".,;:!?)\"']")
        try:
            normalized = normalize_url(raw)
        except UnsafeUrlError:
            continue
        if normalized not in seen:
            seen.add(normalized)
            urls.append(normalized)
        if len(urls) >= max_urls:
            break
    return urls


def normalize_url(url: str) -> str:
    """Validate and normalize a URL; raises UnsafeUrlError if blocked."""
    parsed = urlparse((url or "").strip())
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise UnsafeUrlError(f"Blocked URL scheme: {scheme or '(none)'}")

    host = (parsed.hostname or "").lower().strip(".")
    if not host:
        raise UnsafeUrlError("URL has no hostname")

    if _looks_internal_hostname(host):
        raise UnsafeUrlError("Localhost URLs are not allowed")

    if host.endswith(".local") or host.endswith(".internal"):
        raise UnsafeUrlError("Internal hostnames are not allowed")

    _assert_public_ip(host)

    port = parsed.port
    if port is not None and port not in (80, 443, 8080, 8443):
        raise UnsafeUrlError(f"Blocked port: {port}")

    path = parsed.path or "/"
    if parsed.query:
        return f"{scheme}://{host}{path}?{parsed.query}"
    return f"{scheme}://{host}{path}"


def is_url_safe(url: str) -> bool:
    try:
        normalize_url(url)
        return True
    except (UnsafeUrlError, ValueError):
        return False


def _assert_public_ip(host: str) -> None:
    """Reject private, loopback, link-local, and reserved addresses."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip is not None:
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            raise UnsafeUrlError(f"Blocked private/reserved address: {host}")
        return

    if _looks_internal_hostname(host):
        raise UnsafeUrlError(f"Internal hostname not allowed: {host}")

    try:
        addr_infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # Offline/sandbox: allow public-looking hostnames; fetch will fail if invalid.
        return

    for info in addr_infos:
        ip_str = info[4][0]
        try:
            resolved = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            resolved.is_private
            or resolved.is_loopback
            or resolved.is_link_local
            or resolved.is_reserved
            or resolved.is_multicast
        ):
            raise UnsafeUrlError(f"Blocked private/reserved address: {ip_str}")


def _looks_internal_hostname(host: str) -> bool:
    lower = host.lower()
    if lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    if lower.endswith(".local") or lower.endswith(".internal"):
        return True
    if lower.endswith(".localhost"):
        return True
    return False
