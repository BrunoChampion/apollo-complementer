from app.graph.enrichment_tools import ENRICHMENT_TOOLS, web_search
from app.services.web_search_service import SearchResult, WebSearchService


def test_web_search_returns_snippets(monkeypatch) -> None:
    def fake_search(self, query: str, *, max_results: int) -> list[SearchResult]:
        assert query == "Acme Mexico empleo"
        assert max_results == 3
        return [
            SearchResult(
                title="Acme Careers",
                snippet="Acme esta contratando Customer Success Managers en Mexico.",
                url="https://example.com/result",
            )
        ]

    monkeypatch.setattr(WebSearchService, "_search_duckduckgo", fake_search)

    results = WebSearchService().search("  Acme Mexico empleo  ", max_results=3)

    assert results == [
        {
            "title": "Acme Careers",
            "snippet": "Acme esta contratando Customer Success Managers en Mexico.",
            "url": "https://example.com/result",
        }
    ]


def test_web_search_handles_failure_with_empty_list(monkeypatch) -> None:
    calls = {"count": 0}

    def failing_search(self, query: str, *, max_results: int) -> list[SearchResult]:
        calls["count"] += 1
        raise RuntimeError("duckduckgo unavailable")

    monkeypatch.setattr(WebSearchService, "_search_duckduckgo", failing_search)

    assert WebSearchService().search("Acme careers", max_results=5) == []
    assert calls["count"] == 2


def test_web_search_blank_query_returns_empty_without_network(monkeypatch) -> None:
    def unexpected_search(self, query: str, *, max_results: int) -> list[SearchResult]:
        raise AssertionError("network should not be called for blank query")

    monkeypatch.setattr(WebSearchService, "_search_duckduckgo", unexpected_search)

    assert WebSearchService().search("   ", max_results=5) == []


def test_web_search_job_posting_snippets_mocked(monkeypatch) -> None:
    def fake_search(self, query: str, *, max_results: int) -> list[SearchResult]:
        return [
            SearchResult(
                title="Acme - Analista de Operaciones",
                snippet="Acme busca Analista de Operaciones hibrido en Colombia.",
                url="https://jobs.example.com/acme",
            )
        ]

    monkeypatch.setattr(WebSearchService, "_search_duckduckgo", fake_search)

    results = WebSearchService().search('"Acme" estamos contratando', max_results=5)

    assert len(results) == 1
    assert "busca Analista de Operaciones" in results[0]["snippet"]


def test_langchain_tool_wrapper_uses_web_search(monkeypatch) -> None:
    def fake_search(self, query: str, *, max_results: int) -> list[SearchResult]:
        return [
            SearchResult(
                title="Acme",
                snippet="Acme vende software B2B en Chile.",
                url="https://example.com/acme",
            )
        ]

    monkeypatch.setattr(WebSearchService, "_search_duckduckgo", fake_search)

    if hasattr(web_search, "invoke"):
        results = web_search.invoke({"query": "Acme Chile", "max_results": 1})
    else:
        results = web_search("Acme Chile", 1)

    assert results[0]["title"] == "Acme"
    assert web_search in ENRICHMENT_TOOLS
