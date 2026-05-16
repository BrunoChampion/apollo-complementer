from app.core.langfuse import InMemoryTracer
from app.graph.enrichment_agent_builder import DeterministicEnrichmentAgent


def test_enrichment_agent_records_tool_history_and_spans() -> None:
    tracer = InMemoryTracer()
    agent = DeterministicEnrichmentAgent(
        web_search_tool=lambda query, max_results: [
            {"title": "Acme", "snippet": "Acme vende software B2B.", "url": "https://x"}
        ],
        stack_tool=lambda url: {
            "technologies": [],
            "has_chatbot": False,
            "has_crm": False,
            "has_ecommerce": False,
            "raw_signals": [],
        },
        github_tool=lambda company_domain, company_name=None: {"org_found": False},
        tracer=tracer,
    )

    result = agent.invoke(
        {
            "run_id": "run-1",
            "lead_id": "lead-1",
            "lead": {
                "lead_id": "lead-1",
                "company_name": "Acme",
                "company_website": "https://acme.com",
                "country": "Mexico",
            },
        }
    )

    assert result["iteration_count"] == 3
    assert result["tool_calls_history"][0]["iteration"] == 1
    assert "duration_ms" in result["tool_calls_history"][0]
    assert [span.name for span in tracer.spans] == [
        "enrichment.tool.web_search",
        "enrichment.tool.analyze_website_stack",
        "enrichment.tool.github_search_org",
    ]
