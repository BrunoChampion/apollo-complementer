from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings


@dataclass(frozen=True)
class SearchResult:
    title: str
    snippet: str
    url: str

    def as_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "snippet": self.snippet,
            "url": self.url,
        }


class WebSearchService:
    """Search the public web and return only search engine snippets."""

    def __init__(self, *, timeout_seconds: int | None = None) -> None:
        settings = get_settings()
        self.timeout_seconds = timeout_seconds or settings.web_search_timeout_seconds

    def search(self, query: str, max_results: int | None = None) -> list[dict[str, str]]:
        settings = get_settings()
        limit = max(1, min(max_results or settings.duckduckgo_max_results, 10))
        clean_query = " ".join((query or "").split())
        if not clean_query:
            return []

        for attempt in range(2):
            try:
                return [
                    result.as_dict()
                    for result in self._search_duckduckgo(clean_query, max_results=limit)
                ]
            except Exception:
                if attempt == 1:
                    return []
        return []

    def _search_duckduckgo(self, query: str, *, max_results: int) -> list[SearchResult]:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS(timeout=self.timeout_seconds) as ddgs:
            rows = ddgs.text(query, max_results=max_results)
            results = []
            for row in rows:
                result = _normalize_result(row)
                if result.url:
                    results.append(result)
            return results


def search_web_snippets(query: str, max_results: int | None = None) -> list[dict[str, str]]:
    return WebSearchService().search(query=query, max_results=max_results)


def _normalize_result(row: dict[str, Any]) -> SearchResult:
    return SearchResult(
        title=str(row.get("title") or ""),
        snippet=str(row.get("body") or row.get("snippet") or ""),
        url=str(row.get("href") or row.get("url") or ""),
    )
