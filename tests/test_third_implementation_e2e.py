from app.graph.enrich_and_draft_builder import build_enrich_and_draft_graph
from app.graph.enrichment_agent_builder import (
    DeterministicEnrichmentAgent,
    build_enrichment_agent_graph,
)
from app.graph.revise_builder import build_revise_enriched_draft_graph


def test_third_implementation_enrich_draft_revise_e2e() -> None:
    enrichment_graph = build_enrichment_agent_graph(
        agent=DeterministicEnrichmentAgent(
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
            },
            github_tool=lambda company_domain, company_name=None: {"org_found": False},
        )
    )
    lead = {
        "lead_id": "lead-1",
        "company_name": "Acme",
        "company_website": "https://acme.com",
        "company_domain": "acme.com",
        "prospect_name": "Ana Ruiz",
        "prospect_title": "COO",
        "country": "Mexico",
        "headcount": 50,
    }

    enrichment = enrichment_graph.invoke(
        {"run_id": "run-1", "lead_id": "lead-1", "lead": lead},
        config={"configurable": {"thread_id": "e2e-enrich"}},
    )
    enrichment_result = enrichment["enrichment_result"]
    enrichment_result["recommended_action"] = "draft"
    enrichment_result["confidence_score"] = 90

    draft = build_enrich_and_draft_graph().invoke(
        {
            "run_id": "run-1",
            "lead_id": "lead-1",
            "action": "enrich_and_draft",
            "lead": lead,
            "enrichment_result": enrichment_result,
        },
        config={"configurable": {"thread_id": "e2e-draft"}},
    )

    assert draft["status"] in {"drafted", "needs_revision"}
    assert draft["email_draft"]

    revise = build_revise_enriched_draft_graph().invoke(
        {
            "run_id": "run-1",
            "lead_id": "lead-1",
            "action": "revise",
            "lead": {**lead, "action": "revise", "revision_instruction": "Hazlo mas directo."},
            "enrichment_result": enrichment_result,
            "evidence_items": enrichment_result["evidence_items"],
            "email_draft": draft["email_draft"],
            "previous_draft": draft["email_draft"],
            "revision_instruction": "Hazlo mas directo.",
        },
        config={"configurable": {"thread_id": "e2e-revise"}},
    )

    assert revise["status"] in {"revised", "needs_revision"}
    assert revise.get("revised_draft") or revise.get("email_draft")


def test_third_implementation_brazil_does_not_draft() -> None:
    enrichment_graph = build_enrichment_agent_graph()
    result = enrichment_graph.invoke(
        {
            "run_id": "run-1",
            "lead_id": "lead-br",
            "lead": {
                "lead_id": "lead-br",
                "company_name": "Acme Brasil",
                "country": "Brasil",
            },
        },
        config={"configurable": {"thread_id": "e2e-br"}},
    )

    assert result["enrichment_result"]["recommended_action"] == "discard"
