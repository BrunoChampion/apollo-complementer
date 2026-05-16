from __future__ import annotations

from typing import Any

from app.services.github_org_service import github_search_org_data
from app.services.web_search_service import search_web_snippets
from app.services.website_stack_analyzer import analyze_website_stack_url

try:
    from langchain.tools import tool
except ImportError:

    def tool(func=None, **_: object):
        def decorator(inner):
            return inner

        if func is None:
            return decorator
        return func


@tool
def web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search the public web and return search result snippets only.

    Args:
        query: Search terms for the prospect company.
        max_results: Maximum number of search results to return.
    """
    return search_web_snippets(query=query, max_results=max_results)


@tool
def analyze_website_stack(url: str) -> dict[str, Any]:
    """Analyze a company homepage HTML and detect CRM, chatbot, analytics, and ecommerce signals.

    Args:
        url: Company homepage URL.
    """
    return analyze_website_stack_url(url)


@tool
def github_search_org(company_domain: str, company_name: str | None = None) -> dict[str, Any]:
    """Find a best-effort public GitHub organization for a company.

    Args:
        company_domain: Company domain, such as acme.com.
        company_name: Optional human-readable company name.
    """
    return github_search_org_data(company_domain=company_domain, company_name=company_name)


ENRICHMENT_TOOLS = [web_search, analyze_website_stack, github_search_org]
