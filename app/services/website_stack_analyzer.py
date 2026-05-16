from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings

TECH_SIGNATURES: dict[str, tuple[str, ...]] = {
    "HubSpot": ("hubspot.net", "hs-scripts.com", "js.hsforms.net"),
    "Salesforce": ("salesforce.com", "force.com", "salesforceliveagent.com"),
    "Intercom": ("intercom.io", "intercomcdn.com"),
    "Zendesk": ("zendesk.com", "zdassets.com"),
    "Google Analytics": ("googletagmanager.com", "google-analytics.com", "gtag/js"),
    "Shopify": ("myshopify.com", "cdn.shopify.com", "shopify.com"),
    "WooCommerce": ("woocommerce.com", "woocommerce", "wc-ajax"),
    "WordPress": ("wp-content", "wordpress.org", "wp-includes"),
}

CHATBOT_TECHS = {"Intercom", "Zendesk", "HubSpot"}
CRM_TECHS = {"HubSpot", "Salesforce", "Zendesk"}
ECOMMERCE_TECHS = {"Shopify", "WooCommerce"}


@dataclass(frozen=True)
class WebsiteStackResult:
    technologies: list[str]
    has_chatbot: bool
    has_crm: bool
    has_ecommerce: bool
    raw_signals: list[str]
    status: str = "ok"
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "technologies": self.technologies,
            "has_chatbot": self.has_chatbot,
            "has_crm": self.has_crm,
            "has_ecommerce": self.has_ecommerce,
            "raw_signals": self.raw_signals,
            "status": self.status,
            "error": self.error,
        }


def analyze_website_stack_url(url: str) -> dict[str, Any]:
    analyzer = WebsiteStackAnalyzer()
    return analyzer.analyze(url)


class WebsiteStackAnalyzer:
    """Detect common GTM, CRM, chat, CMS, and ecommerce signals from homepage HTML."""

    def __init__(self, *, timeout_seconds: int | None = None, max_html_bytes: int | None = None):
        settings = get_settings()
        self.timeout_seconds = timeout_seconds or settings.web_search_timeout_seconds
        self.max_html_bytes = max_html_bytes or settings.enrichment_max_html_bytes

    def analyze(self, url: str) -> dict[str, Any]:
        normalized_url = _normalize_url(url)
        if not normalized_url:
            return _error_result("url is required").as_dict()

        try:
            html = self._fetch_homepage_html(normalized_url)
        except Exception as exc:
            return _error_result(str(exc)).as_dict()

        return detect_website_stack(html).as_dict()

    def _fetch_homepage_html(self, url: str) -> str:
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            with client.stream(
                "GET",
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"
                    )
                },
            ) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type.lower():
                    raise ValueError(f"Non-HTML content: {content_type}")

                chunks = bytearray()
                for chunk in response.iter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > self.max_html_bytes:
                        chunks = chunks[: self.max_html_bytes]
                        break
                return chunks.decode(response.encoding or "utf-8", errors="ignore")


def detect_website_stack(html: str) -> WebsiteStackResult:
    lower_html = (html or "").lower()
    technologies: list[str] = []
    raw_signals: list[str] = []

    for technology, signatures in TECH_SIGNATURES.items():
        matched = [signature for signature in signatures if signature.lower() in lower_html]
        if matched:
            technologies.append(technology)
            raw_signals.extend(matched)

    technologies = sorted(set(technologies))
    raw_signals = sorted(set(raw_signals))
    return WebsiteStackResult(
        technologies=technologies,
        has_chatbot=bool(CHATBOT_TECHS.intersection(technologies)),
        has_crm=bool(CRM_TECHS.intersection(technologies)),
        has_ecommerce=bool(ECOMMERCE_TECHS.intersection(technologies)),
        raw_signals=raw_signals,
    )


def _normalize_url(url: str | None) -> str:
    normalized = (url or "").strip()
    if not normalized:
        return ""
    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"
    return normalized


def _error_result(error: str) -> WebsiteStackResult:
    return WebsiteStackResult(
        technologies=[],
        has_chatbot=False,
        has_crm=False,
        has_ecommerce=False,
        raw_signals=[],
        status="error",
        error=error,
    )
