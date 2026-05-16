import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura

from app.core.config import get_settings

DEFAULT_TIMEOUT_SECONDS = 20
MAX_URLS_PER_LEAD = 5

SUFFIXES = {
    "about": ["/about", "/about-us", "/team", "/company"],
    "pricing": ["/pricing", "/plans", "/precios"],
    "careers": ["/careers", "/jobs", "/work-with-us", "/join-us"],
    "blog": ["/blog", "/news", "/insights"],
    "help": ["/help", "/docs", "/documentation", "/knowledge-base", "/support"],
}


def _normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url.rstrip("/")


def discover_urls(website: str | None, company_domain: str | None) -> list[str]:
    """Discover a limited set of public URLs for a company."""
    base = _normalize_url(website or f"https://{company_domain}")
    if not base:
        return []

    candidates = [base]
    for suffix_list in SUFFIXES.values():
        if suffix_list:
            candidates.append(urljoin(base + "/", suffix_list[0]))

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for url in candidates:
        parsed = urlparse(url)
        key = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if key not in seen:
            seen.add(key)
            unique.append(url)

    max_urls = get_settings().enrichment_max_urls_per_lead or MAX_URLS_PER_LEAD
    return unique[:max_urls]


def fetch_url_text(
    url: str,
    *,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Fetch a single URL and extract readable text.

    Returns a dict with keys:
    - url: requested URL
    - status: "ok" | "error" | "blocked"
    - text: extracted text (may be empty)
    - error: error message if any
    """
    settings = get_settings()
    timeout = timeout or settings.enrichment_http_timeout_seconds or DEFAULT_TIMEOUT_SECONDS

    # Basic guardrail: do not fetch common non-page assets
    lower = url.lower()
    if lower.endswith((".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".css", ".js")):
        return {"url": url, "status": "blocked", "text": "", "error": "Non-HTML asset"}

    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True, headers={
            "User-Agent": "NYVEX-RevenueOpsCopilot/1.0 ( research bot )",
        })
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return {
            "url": url,
            "status": "error",
            "text": "",
            "error": f"HTTP {exc.response.status_code}",
        }
    except httpx.RequestError as exc:
        return {"url": url, "status": "error", "text": "", "error": str(exc)}

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type.lower():
        return {
            "url": url,
            "status": "blocked",
            "text": "",
            "error": f"Non-HTML content: {content_type}",
        }

    html = response.text
    text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    text = re.sub(r"\s+", " ", text).strip()

    return {"url": url, "status": "ok", "text": text, "error": None}


def fetch_company_pages(
    website: str | None,
    company_domain: str | None,
) -> list[dict[str, Any]]:
    """Discover and fetch public pages for a company.

    Returns a list of result dicts (one per URL attempt).
    """
    urls = discover_urls(website, company_domain)
    results = []
    for url in urls:
        result = fetch_url_text(url)
        results.append(result)
        if result["status"] == "ok" and result["text"]:
            # Stop early if we already have good content
            pass
    return results
