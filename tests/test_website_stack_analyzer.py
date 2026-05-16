from app.graph.enrichment_tools import ENRICHMENT_TOOLS, analyze_website_stack
from app.services.website_stack_analyzer import WebsiteStackAnalyzer, detect_website_stack


def test_analyze_website_stack_detects_hubspot() -> None:
    html = """
    <html>
      <script src="https://js.hs-scripts.com/123.js"></script>
      <script src="https://www.googletagmanager.com/gtm.js"></script>
    </html>
    """

    result = detect_website_stack(html).as_dict()

    assert "HubSpot" in result["technologies"]
    assert "Google Analytics" in result["technologies"]
    assert result["has_crm"] is True
    assert result["has_chatbot"] is True
    assert result["has_ecommerce"] is False


def test_analyze_website_stack_detects_ecommerce_and_wordpress() -> None:
    html = """
    <html>
      <link href="/wp-content/themes/site/style.css" />
      <script src="https://cdn.shopify.com/storefront.js"></script>
    </html>
    """

    result = detect_website_stack(html).as_dict()

    assert result["technologies"] == ["Shopify", "WordPress"]
    assert result["has_ecommerce"] is True
    assert result["has_crm"] is False


def test_website_stack_analyzer_fetches_homepage(monkeypatch) -> None:
    def fake_fetch(self, url: str) -> str:
        assert url == "https://acme.com"
        return "<html><script src='https://widget.intercom.io/widget/abc'></script></html>"

    monkeypatch.setattr(WebsiteStackAnalyzer, "_fetch_homepage_html", fake_fetch)

    result = WebsiteStackAnalyzer().analyze("acme.com")

    assert result["status"] == "ok"
    assert "Intercom" in result["technologies"]
    assert result["has_chatbot"] is True


def test_analyze_website_stack_limits_download_size(monkeypatch) -> None:
    def fake_fetch(self, url: str) -> str:
        html = "x" * 100 + "hubspot.net"
        return html[: self.max_html_bytes]

    monkeypatch.setattr(WebsiteStackAnalyzer, "_fetch_homepage_html", fake_fetch)

    result = WebsiteStackAnalyzer(max_html_bytes=50).analyze("https://large.example.com")

    assert result["status"] == "ok"
    assert result["technologies"] == []


def test_website_stack_analyzer_handles_fetch_error(monkeypatch) -> None:
    def fake_fetch(self, url: str) -> str:
        raise ValueError("Non-HTML content: application/json")

    monkeypatch.setattr(WebsiteStackAnalyzer, "_fetch_homepage_html", fake_fetch)

    result = WebsiteStackAnalyzer().analyze("https://acme.com")

    assert result["status"] == "error"
    assert "Non-HTML" in result["error"]


def test_analyze_website_stack_tool_wrapper(monkeypatch) -> None:
    def fake_fetch(self, url: str) -> str:
        return "<html>zendesk.com</html>"

    monkeypatch.setattr(WebsiteStackAnalyzer, "_fetch_homepage_html", fake_fetch)

    if hasattr(analyze_website_stack, "invoke"):
        result = analyze_website_stack.invoke({"url": "https://tool.example.com"})
    else:
        result = analyze_website_stack("https://tool.example.com")

    assert "Zendesk" in result["technologies"]
    assert analyze_website_stack in ENRICHMENT_TOOLS
