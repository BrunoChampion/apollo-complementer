from app.domain.enrichment import RecommendedAction
from app.graph.enrichment_agent_builder import (
    DeterministicEnrichmentAgent,
    build_enrichment_agent_graph,
)


def _agent() -> DeterministicEnrichmentAgent:
    return DeterministicEnrichmentAgent(
        web_search_tool=lambda query, max_results: [
            {
                "title": "Acme Mexico",
                "snippet": "Acme vende software B2B para empresas en Mexico.",
                "url": "https://search.example/acme",
            }
        ],
        stack_tool=lambda url: {
            "technologies": ["HubSpot"],
            "has_chatbot": True,
            "has_crm": True,
            "has_ecommerce": False,
            "raw_signals": ["hubspot.net"],
            "status": "ok",
            "error": None,
        },
        github_tool=lambda company_domain, company_name=None: {
            "org_found": False,
            "org_name": None,
            "public_repos": 0,
            "top_languages": [],
            "recent_activity": False,
            "status": "ok",
            "error": None,
        },
    )


def test_agent_returns_structured_enrichment_result() -> None:
    graph = build_enrichment_agent_graph(agent=_agent())
    result = graph.invoke(
        {
            "run_id": "run-1",
            "lead_id": "lead-1",
            "lead": {
                "lead_id": "lead-1",
                "company_name": "Acme",
                "company_website": "https://acme.com",
                "company_domain": "acme.com",
                "country": "Mexico",
                "prospect_title": "COO",
                "headcount": 50,
            },
        },
        config={"configurable": {"thread_id": "agent-test"}},
    )

    enrichment = result["enrichment_result"]
    assert enrichment["company_name"] == "Acme"
    assert enrichment["evidence_count"] >= 1
    assert result["iteration_count"] == 3
    assert len(result["tool_calls_history"]) == 3


def test_agent_discards_brazil() -> None:
    graph = build_enrichment_agent_graph(agent=_agent())
    result = graph.invoke(
        {
            "run_id": "run-1",
            "lead_id": "lead-brazil",
            "lead": {
                "lead_id": "lead-brazil",
                "company_name": "Acme Brasil",
                "country": "Brazil",
            },
        },
        config={"configurable": {"thread_id": "agent-brazil"}},
    )

    assert result["enrichment_result"]["recommended_action"] == RecommendedAction.DISCARD.value
    assert result["iteration_count"] == 0


def test_agent_falls_back_to_needs_manual_research() -> None:
    graph = build_enrichment_agent_graph(
        agent=DeterministicEnrichmentAgent(
            web_search_tool=lambda query, max_results: [],
            stack_tool=lambda url: {
                "technologies": [],
                "has_chatbot": False,
                "has_crm": False,
                "has_ecommerce": False,
                "raw_signals": [],
                "status": "ok",
                "error": None,
            },
            github_tool=lambda company_domain, company_name=None: {
                "org_found": False,
                "org_name": None,
                "public_repos": 0,
                "top_languages": [],
                "recent_activity": False,
                "status": "ok",
                "error": None,
            },
        )
    )
    result = graph.invoke(
        {
            "run_id": "run-1",
            "lead_id": "lead-empty",
            "lead": {
                "lead_id": "lead-empty",
                "company_name": "EmptyCo",
                "company_website": "https://empty.example",
                "country": "Colombia",
            },
        },
        config={"configurable": {"thread_id": "agent-empty"}},
    )

    assert result["enrichment_result"]["recommended_action"] in {
        RecommendedAction.NEEDS_MANUAL_RESEARCH.value,
        RecommendedAction.DISCARD.value,
    }
    assert "insufficient_data" in result["enrichment_result"]["risk_flags"]
