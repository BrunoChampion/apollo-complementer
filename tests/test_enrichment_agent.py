import json

import respx
from httpx import Response

from app.domain.enrichment import EnrichmentStatus, RecommendedAction
from app.graph.enrichment_builder import build_enrichment_graph
from app.graph.enrichment_llm import DeterministicEnrichmentLLM, OpenAIEnrichmentLLM
from app.graph.enrichment_nodes import (
    validate_enrichment_input,
    validate_enrichment_output,
    write_enrichment_result,
)


class TestDeterministicEnrichmentLLM:
    def test_weak_input_returns_insufficient_data(self) -> None:
        llm = DeterministicEnrichmentLLM()
        result = llm.enrich_company(
            enrichment_id="test-1",
            run_id="run-1",
            lead_id="lead-1",
            company_name="Acme Corp",
            company_website=None,
            company_domain=None,
            prospect_name="John",
            prospect_title="CEO",
            industry=None,
            country=None,
            manual_context=None,
            web_results=[],
        )
        assert result.enrichment_status == EnrichmentStatus.INSUFFICIENT_DATA
        assert result.recommended_action == RecommendedAction.NEEDS_MANUAL_RESEARCH
        assert result.confidence_score == 0
        assert result.evidence_items == []
        assert "insufficient_data" in (result.risk_flags or [])

    def test_strong_input_returns_evidence_and_draft(self) -> None:
        llm = DeterministicEnrichmentLLM(min_confidence_to_draft=60)
        result = llm.enrich_company(
            enrichment_id="test-2",
            run_id="run-1",
            lead_id="lead-1",
            company_name="Acme Corp",
            company_website="https://acme.com",
            company_domain="acme.com",
            prospect_name="John",
            prospect_title="CEO",
            industry="Software",
            country="Argentina",
            manual_context="Fast growing B2B SaaS platform for enterprise clients.",
            web_results=[
                {
                    "url": "https://acme.com",
                    "status": "ok",
                    "text": "Acme provides B2B software solutions for enterprises.",
                },
                {
                    "url": "https://acme.com/about",
                    "status": "ok",
                    "text": "Founded in 2020, serving 500+ enterprise clients.",
                },
                {
                    "url": "https://acme.com/pricing",
                    "status": "ok",
                    "text": "Custom enterprise pricing available.",
                },
            ],
        )
        assert result.enrichment_status == EnrichmentStatus.ENRICHED
        assert result.recommended_action == RecommendedAction.DRAFT
        assert result.confidence_score is not None
        assert result.confidence_score >= 60
        assert len(result.evidence_items or []) >= 2
        assert result.b2b_fit is True

    def test_single_evidence_below_threshold(self) -> None:
        llm = DeterministicEnrichmentLLM(min_confidence_to_draft=70)
        result = llm.enrich_company(
            enrichment_id="test-3",
            run_id="run-1",
            lead_id="lead-1",
            company_name="Acme Corp",
            company_website="https://acme.com",
            company_domain="acme.com",
            prospect_name=None,
            prospect_title=None,
            industry=None,
            country=None,
            manual_context=None,
            web_results=[
                {
                    "url": "https://acme.com",
                    "status": "ok",
                    "text": "We are a small consultancy.",
                },
            ],
        )
        # 1 evidence item -> confidence 60, below threshold 70
        assert result.recommended_action == RecommendedAction.NEEDS_MANUAL_RESEARCH
        assert result.enrichment_status == EnrichmentStatus.NEEDS_REVIEW


class TestOpenAIEnrichmentLLM:
    @respx.mock
    def test_parse_json_response(self) -> None:
        route = respx.post("https://api.openai.com/v1/responses").mock(
            return_value=Response(
                200,
                json={
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(
                                        {
                                            "company_summary": "B2B SaaS company",
                                            "b2b_fit": True,
                                            "operational_pain_hypothesis": "Scaling support",
                                            "possible_ai_use_case": "AI support bot",
                                            "personalization_angle": "Mention scaling",
                                            "trigger_summary": "Growing fast",
                                            "risk_flags": [],
                                            "evidence_items": [
                                                {
                                                    "claim": "B2B SaaS",
                                                    "source_type": "website",
                                                    "source_url": "https://acme.com",
                                                    "quote_or_summary": "We serve enterprises",
                                                    "confidence": 70,
                                                    "used_in_message": True,
                                                }
                                            ],
                                            "confidence_score": 70,
                                            "recommended_action": "draft",
                                        }
                                    ),
                                }
                            ]
                        }
                    ]
                },
            )
        )
        llm = OpenAIEnrichmentLLM(
            api_key="fake-key",
            model="gpt-test",
            reasoning_effort="low",
            require_evidence=True,
            min_confidence_to_draft=65,
        )
        result = llm.enrich_company(
            enrichment_id="test-oai",
            run_id="run-1",
            lead_id="lead-1",
            company_name="Acme Corp",
            company_website="https://acme.com",
            company_domain="acme.com",
            prospect_name=None,
            prospect_title=None,
            industry=None,
            country=None,
            manual_context=None,
            web_results=[],
        )
        assert result.enrichment_status == EnrichmentStatus.ENRICHED
        assert result.recommended_action == RecommendedAction.DRAFT
        assert result.confidence_score == 70
        assert len(result.evidence_items or []) == 1
        assert route.called

    @respx.mock
    def test_low_confidence_overridden_to_needs_manual_research(self) -> None:
        route = respx.post("https://api.openai.com/v1/responses").mock(
            return_value=Response(
                200,
                json={
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(
                                        {
                                            "company_summary": "Unknown",
                                            "b2b_fit": None,
                                            "evidence_items": [
                                                {
                                                    "claim": "Something",
                                                    "source_type": "website",
                                                    "confidence": 40,
                                                    "used_in_message": False,
                                                }
                                            ],
                                            "confidence_score": 40,
                                            "recommended_action": "draft",
                                        }
                                    ),
                                }
                            ]
                        }
                    ]
                },
            )
        )
        llm = OpenAIEnrichmentLLM(
            api_key="fake-key",
            model="gpt-test",
            reasoning_effort="low",
            require_evidence=True,
            min_confidence_to_draft=65,
        )
        result = llm.enrich_company(
            enrichment_id="test-oai-2",
            run_id="run-1",
            lead_id="lead-1",
            company_name="Acme Corp",
            company_website="https://acme.com",
            company_domain="acme.com",
            prospect_name=None,
            prospect_title=None,
            industry=None,
            country=None,
            manual_context=None,
            web_results=[],
        )
        # confidence 40 < 65 -> overridden
        assert result.recommended_action == RecommendedAction.NEEDS_MANUAL_RESEARCH
        assert route.called

    @respx.mock
    def test_no_evidence_returns_insufficient_data(self) -> None:
        route = respx.post("https://api.openai.com/v1/responses").mock(
            return_value=Response(
                200,
                json={
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(
                                        {
                                            "company_summary": None,
                                            "b2b_fit": None,
                                            "evidence_items": [],
                                            "confidence_score": 10,
                                            "recommended_action": "draft",
                                        }
                                    ),
                                }
                            ]
                        }
                    ]
                },
            )
        )
        llm = OpenAIEnrichmentLLM(
            api_key="fake-key",
            model="gpt-test",
            reasoning_effort="low",
            require_evidence=True,
            min_confidence_to_draft=65,
        )
        result = llm.enrich_company(
            enrichment_id="test-oai-3",
            run_id="run-1",
            lead_id="lead-1",
            company_name="Acme Corp",
            company_website="https://acme.com",
            company_domain="acme.com",
            prospect_name=None,
            prospect_title=None,
            industry=None,
            country=None,
            manual_context=None,
            web_results=[],
        )
        assert result.enrichment_status == EnrichmentStatus.INSUFFICIENT_DATA
        assert result.recommended_action == RecommendedAction.NEEDS_MANUAL_RESEARCH
        assert route.called


class TestEnrichmentNodes:
    def test_validate_input_missing_company_name(self) -> None:
        state = {"run_id": "r1", "lead_id": "l1", "lead": {}}
        result = validate_enrichment_input(state)
        assert result["status"] == "error"
        assert "company_name" in str(result["error_message"])

    def test_validate_input_ok(self) -> None:
        state = {"run_id": "r1", "lead_id": "l1", "lead": {"company_name": "Acme"}}
        result = validate_enrichment_input(state)
        assert result["status"] == "validated"
        assert "enrichment_id" in result

    def test_validate_output_no_evidence(self) -> None:
        state = {
            "run_id": "r1",
            "lead_id": "l1",
            "lead": {"company_name": "Acme"},
            "enrichment_result": {
                "enrichment_id": "e1",
                "enrichment_status": "enriched",
                "recommended_action": "draft",
                "evidence_items": [],
            },
        }
        result = validate_enrichment_output(state)
        assert result["status"] == "insufficient_data"
        assert result["enrichment_result"]["recommended_action"] == "needs_manual_research"

    def test_validate_output_with_evidence(self) -> None:
        state = {
            "run_id": "r1",
            "lead_id": "l1",
            "lead": {"company_name": "Acme"},
            "enrichment_result": {
                "enrichment_id": "e1",
                "enrichment_status": "enriched",
                "recommended_action": "draft",
                "evidence_items": [
                    {
                        "claim": "B2B SaaS",
                        "source_type": "website",
                        "confidence": 70,
                        "used_in_message": True,
                    }
                ],
            },
        }
        result = validate_enrichment_output(state)
        assert result["status"] == "validated_output"

    def test_write_result_success(self) -> None:
        state = {
            "run_id": "r1",
            "lead_id": "l1",
            "lead": {"company_name": "Acme"},
            "enrichment_result": {
                "enrichment_status": "enriched",
                "confidence_score": 75,
                "recommended_action": "draft",
            },
        }
        result = write_enrichment_result(state)
        assert "Enrichment complete" in result["agent_note"]
        assert "draft" in result["agent_note"]

    def test_write_result_error(self) -> None:
        state = {
            "run_id": "r1",
            "lead_id": "l1",
            "lead": {"company_name": "Acme"},
            "status": "error",
            "error_message": "Something broke",
        }
        result = write_enrichment_result(state)
        assert "failed" in result["agent_note"]


class TestEnrichmentGraph:
    @respx.mock
    def test_graph_runs_with_deterministic_llm(self) -> None:
        urls = [
            "https://acme.com",
            "https://acme.com/about",
            "https://acme.com/pricing",
            "https://acme.com/careers",
            "https://acme.com/blog",
        ]
        for url in urls:
            respx.get(url).mock(
                return_value=Response(
                    200,
                    text=f"<html><body><p>Content from {url}</p></body></html>",
                    headers={"content-type": "text/html"},
                )
            )

        graph = build_enrichment_graph()
        state = {
            "run_id": "r1",
            "lead_id": "l1",
            "lead": {
                "company_name": "Acme",
                "company_website": "https://acme.com",
                "company_domain": "acme.com",
                "country": "Argentina",
                "headcount": 50,
                "prospect_title": "COO",
            },
        }
        result = graph.invoke(state, config={"configurable": {"thread_id": "test"}})
        assert "agent_note" in result
        assert "Enrichment complete" in result["agent_note"]
        result_dict = result.get("enrichment_result", {})
        assert len(result_dict.get("evidence_items", [])) >= 1

    @respx.mock
    def test_graph_with_no_company_name_errors(self) -> None:
        graph = build_enrichment_graph()
        state = {
            "run_id": "r1",
            "lead_id": "l1",
            "lead": {},
        }
        result = graph.invoke(state, config={"configurable": {"thread_id": "test"}})
        assert result["status"] == "error"
        assert "failed" in result.get("agent_note", "")

    @respx.mock
    def test_graph_with_failed_http_returns_insufficient_data(self) -> None:
        urls = [
            "https://empty.com",
            "https://empty.com/about",
            "https://empty.com/pricing",
            "https://empty.com/careers",
            "https://empty.com/blog",
        ]
        for url in urls:
            respx.get(url).mock(return_value=Response(500))

        graph = build_enrichment_graph()
        state = {
            "run_id": "r1",
            "lead_id": "l1",
            "lead": {
                "company_name": "Empty",
                "company_website": "https://empty.com",
                "company_domain": "empty.com",
            },
        }
        result = graph.invoke(state, config={"configurable": {"thread_id": "test"}})
        assert "agent_note" in result
        result_dict = result.get("enrichment_result", {})
        assert result_dict.get("enrichment_status") == "insufficient_data"
        assert result_dict.get("recommended_action") == "discard"


class TestLLMFactory:
    def test_build_enrichment_llm_deterministic_by_default(self) -> None:
        from app.core.config import Settings
        from app.graph.llm_factory import build_enrichment_llm

        settings = Settings(enrichment_provider="deterministic")
        llm = build_enrichment_llm(settings)
        assert isinstance(llm, DeterministicEnrichmentLLM)

    def test_build_enrichment_llm_openai_without_key_falls_back(self) -> None:
        from app.core.config import Settings
        from app.graph.llm_factory import build_enrichment_llm

        settings = Settings(
            enrichment_provider="openai",
            openai_api_key="",
            enrichment_min_confidence_to_draft=70,
        )
        llm = build_enrichment_llm(settings)
        assert isinstance(llm, DeterministicEnrichmentLLM)

    def test_build_enrichment_llm_openai_with_key(self) -> None:
        from app.core.config import Settings
        from app.graph.llm_factory import build_enrichment_llm

        settings = Settings(
            enrichment_provider="openai",
            openai_api_key="sk-test",
            enrichment_model="gpt-test",
            enrichment_reasoning_effort="low",
            enrichment_min_confidence_to_draft=70,
            enrichment_require_evidence=True,
        )
        llm = build_enrichment_llm(settings)
        assert isinstance(llm, OpenAIEnrichmentLLM)
