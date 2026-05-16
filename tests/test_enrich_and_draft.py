import respx

from app.domain.enrichment import EnrichmentResult, EnrichmentStatus, RecommendedAction
from app.domain.leads import LeadAction, LeadRow, LeadStatus
from app.services.enrich_and_draft_service import EnrichAndDraftService


def _ready_fields(company_name: str = "Acme Corp", prospect_name: str = "Juan Perez") -> dict:
    return {
        "company_linkedin_url": "https://www.linkedin.com/company/acme-corp/",
        "prospect_linkedin_url": "https://www.linkedin.com/in/juan-perez/",
        "manual_company_linkedin_text": (
            f"{company_name} is a B2B software company with support, onboarding, "
            "implementation and documentation workflows for clients."
        ),
        "manual_person_linkedin_text": (
            f"{prospect_name} is COO at {company_name} and works on operations."
        ),
        "company_size": "50",
        "industry": "SaaS B2B",
    }


class TestEnrichAndDraftService:
    @respx.mock
    def test_good_enrichment_produces_draft(self) -> None:
        enrichment = EnrichmentResult(
            enrichment_id="e-good",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="Acme Corp",
            company_website="https://acme.com",
            b2b_fit=True,
            operational_pain_hypothesis=(
                "el conocimiento queda repartido entre soporte, onboarding y documentación"
            ),
            confidence_score=90,
            recommended_action=RecommendedAction.DRAFT,
            evidence_items=[
                {
                    "claim": (
                        "Acme Corp has support, onboarding and documentation workflows "
                        "for B2B clients"
                    ),
                    "source_type": "manual_context",
                    "confidence": 90,
                }
            ],
        )
        service = EnrichAndDraftService()
        result = service.draft_graph.invoke(
            {
                "run_id": "run-1",
                "lead_id": "lead-1",
                "action": "enrich_and_draft",
                "lead": {
                    "lead_id": "lead-1",
                    "company_name": "Acme Corp",
                    "company_website": "https://acme.com",
                    "prospect_name": "Juan Perez",
                    "prospect_title": "COO",
                    "country": "Argentina",
                },
                "enrichment_result": enrichment.model_dump(mode="json"),
            },
            config={"configurable": {"thread_id": "test-good-enrichment"}},
        )

        assert result["status"] == "drafted"
        assert result["email_draft"] is not None
        assert result["email_subject"] is not None
        assert result["agent_note"] is not None

    @respx.mock
    def test_no_website_returns_insufficient_data(self) -> None:
        service = EnrichAndDraftService()
        lead = LeadRow(
            lead_id="lead-2",
            company_name="Mystery Co",
            action=LeadAction.ENRICH_AND_DRAFT,
            status=LeadStatus.NEW,
        )
        result = service.enrich_and_draft(lead, run_id="run-1")

        assert result["lead_id"] == "lead-2"
        assert result["status"] == "needs_manual_research"
        assert result.get("email_draft") is None
        assert "blocked before web research" in result["agent_note"]

    @respx.mock
    def test_low_confidence_returns_needs_manual_research(self) -> None:
        # Build enrichment result directly to bypass web fetch
        enrichment = EnrichmentResult(
            enrichment_id="e1",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="WeakCo",
            company_website="https://weakco.com",
            b2b_fit=True,
            confidence_score=40,
            recommended_action=RecommendedAction.NEEDS_MANUAL_RESEARCH,
            evidence_items=[
                {
                    "claim": "Something vague",
                    "source_type": "website",
                    "confidence": 40,
                }
            ],
        )

        service = EnrichAndDraftService()
        # Inject enrichment result directly into state to test gating
        draft_state = {
            "run_id": "run-1",
            "lead_id": "lead-3",
            "action": "enrich_and_draft",
            "lead": {
                "lead_id": "lead-3",
                "company_name": "WeakCo",
                "company_website": "https://weakco.com",
                "prospect_name": "Ana",
                "prospect_title": "CEO",
                "country": "Argentina",
            },
            "enrichment_result": enrichment.model_dump(mode="json"),
        }
        draft_output = service.draft_graph.invoke(
            draft_state,
            config={"configurable": {"thread_id": "test-low-conf"}},
        )

        assert draft_output["status"] == "needs_manual_research"
        assert "No draft generated" in draft_output["agent_note"]

    @respx.mock
    def test_no_evidence_returns_needs_manual_research(self) -> None:
        enrichment = EnrichmentResult(
            enrichment_id="e2",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="EmptyCo",
            company_website="https://emptyco.com",
            b2b_fit=True,
            confidence_score=80,
            recommended_action=RecommendedAction.DRAFT,
            evidence_items=[],
        )

        service = EnrichAndDraftService()
        draft_state = {
            "run_id": "run-1",
            "lead_id": "lead-4",
            "action": "enrich_and_draft",
            "lead": {
                "lead_id": "lead-4",
                "company_name": "EmptyCo",
                "company_website": "https://emptyco.com",
                "prospect_name": "Pedro",
                "prospect_title": "CTO",
                "country": "Mexico",
            },
            "enrichment_result": enrichment.model_dump(mode="json"),
        }
        draft_output = service.draft_graph.invoke(
            draft_state,
            config={"configurable": {"thread_id": "test-no-ev"}},
        )

        assert draft_output["status"] == "needs_manual_research"
        assert "No draft generated" in draft_output["agent_note"]

    @respx.mock
    def test_decorative_evidence_blocks_draft(self) -> None:
        enrichment = EnrichmentResult(
            enrichment_id="e3",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="DecorativeCo",
            company_website="https://decorative.example",
            b2b_fit=True,
            confidence_score=90,
            recommended_action=RecommendedAction.DRAFT,
            evidence_items=[
                {
                    "claim": "DecorativeCo has an office in Mexico",
                    "source_type": "website",
                    "confidence": 90,
                }
            ],
        )

        service = EnrichAndDraftService()
        draft_output = service.draft_graph.invoke(
            {
                "run_id": "run-1",
                "lead_id": "lead-decorative",
                "action": "enrich_and_draft",
                "lead": {
                    "lead_id": "lead-decorative",
                    "company_name": "DecorativeCo",
                    "company_website": "https://decorative.example",
                    "prospect_name": "Ana",
                    "prospect_title": "CEO",
                    "country": "Mexico",
                },
                "enrichment_result": enrichment.model_dump(mode="json"),
            },
            config={"configurable": {"thread_id": "test-decorative-signal"}},
        )

        assert draft_output["status"] == "needs_manual_research"
        assert "operational signal" in draft_output["agent_note"]

    @respx.mock
    def test_service_returns_enrichment_dict_on_gate(self) -> None:
        service = EnrichAndDraftService()
        lead = LeadRow(
            lead_id="lead-5",
            company_name="NoWeb",
            action=LeadAction.ENRICH_AND_DRAFT,
            status=LeadStatus.NEW,
        )
        result = service.enrich_and_draft(lead, run_id="run-1")

        assert result["status"] == "needs_manual_research"
        assert "enrichment_result" not in result
