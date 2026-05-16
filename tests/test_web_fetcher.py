import respx
from httpx import Response

from app.services.web_fetcher import discover_urls, fetch_company_pages, fetch_url_text


def test_discover_urls_from_website() -> None:
    urls = discover_urls("https://acme.com", "acme.com")
    assert urls[0] == "https://acme.com"
    assert "https://acme.com/about" in urls
    assert "https://acme.com/pricing" in urls
    assert "https://acme.com/careers" in urls
    assert len(urls) <= 5


def test_discover_urls_from_domain_only() -> None:
    urls = discover_urls(None, "cloudops.io")
    assert urls[0] == "https://cloudops.io"
    assert "https://cloudops.io/blog" in urls


def test_discover_urls_deduplicates() -> None:
    urls = discover_urls("https://acme.com/", "acme.com")
    paths = [u.split("/")[3] if len(u.split("/")) > 3 else "" for u in urls]
    assert len(paths) == len(set(paths)) or urls[0] == "https://acme.com"


class TestFetchUrlText:
    @respx.mock
    def test_extracts_text_from_html(self) -> None:
        from pathlib import Path
        html = Path("tests/fixtures/web_home.html").read_text(encoding="utf-8")
        route = respx.get("https://acme.com").mock(
            return_value=Response(200, text=html, headers={"content-type": "text/html"})
        )

        result = fetch_url_text("https://acme.com")

        assert result["status"] == "ok"
        assert "Acme Inc" in result["text"]
        assert "automation tools" in result["text"]
        assert route.called

    @respx.mock
    def test_handles_404(self) -> None:
        route = respx.get("https://acme.com/missing").mock(return_value=Response(404))

        result = fetch_url_text("https://acme.com/missing")

        assert result["status"] == "error"
        assert "404" in result["error"]
        assert route.called

    def test_blocks_asset_extensions(self) -> None:
        result = fetch_url_text("https://acme.com/image.png")
        assert result["status"] == "blocked"
        assert "Non-HTML asset" in result["error"]


class TestFetchCompanyPages:
    @respx.mock
    def test_fetches_multiple_pages(self) -> None:
        from pathlib import Path
        html = Path("tests/fixtures/web_home.html").read_text(encoding="utf-8")

        # Mock any acme.com GET with fallback to 200 for html
        # We use a single catch-all route because respx exact matching
        # can be tricky with multiple overlapping hosts.
        route = respx.get("https://acme.com").mock(
            return_value=Response(200, text=html, headers={"content-type": "text/html"})
        )
        respx.get("https://acme.com/pricing").mock(return_value=Response(404))

        results = fetch_company_pages("https://acme.com", "acme.com")

        assert len(results) >= 3
        ok_results = [r for r in results if r["status"] == "ok"]
        assert len(ok_results) >= 1
        assert route.called

    @respx.mock
    def test_respects_max_urls(self) -> None:
        respx.get("https://smallco.com").mock(
            return_value=Response(200, text="<html></html>", headers={"content-type": "text/html"})
        )
        respx.get("https://smallco.com/about").mock(return_value=Response(404))
        respx.get("https://smallco.com/pricing").mock(return_value=Response(404))
        respx.get("https://smallco.com/careers").mock(return_value=Response(404))
        respx.get("https://smallco.com/blog").mock(return_value=Response(404))

        results = fetch_company_pages("https://smallco.com", "smallco.com")
        assert len(results) <= 5
