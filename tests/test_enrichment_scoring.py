from app.domain.enrichment import (
    EnrichmentResult,
    EnrichmentStatus,
    EvidenceItem,
    EvidenceSourceType,
    RecommendedAction,
)
from app.services.enrichment_scoring import score_enrichment_result


class TestEnrichmentScoringPositiveCases:
    def test_strong_b2b_latam_coo_with_evidence_gets_draft(self) -> None:
        result = EnrichmentResult(
            enrichment_id="e1",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="Acme Corp",
            company_website="https://acme.com",
            prospect_name="Juan Perez",
            prospect_title="COO",
            b2b_fit=True,
            confidence_score=75,
            evidence_items=[
                EvidenceItem(
                    claim="Hiring ops team",
                    source_type=EvidenceSourceType.CAREERS,
                    confidence=70,
                ),
                EvidenceItem(
                    claim="B2B platform",
                    source_type=EvidenceSourceType.WEBSITE,
                    confidence=80,
                ),
                EvidenceItem(
                    claim="Expanding to Mexico",
                    source_type=EvidenceSourceType.BLOG,
                    confidence=65,
                ),
            ],
        )
        score = score_enrichment_result(result, lead_data={"country": "Argentina", "headcount": 50})
        assert score.recommended_action == RecommendedAction.DRAFT
        assert score.score >= 75
        assert score.confidence_score >= 65
        assert any("LATAM" in r for r in score.score_reasons)
        assert any("tier A" in r for r in score.score_reasons)

    def test_medium_sized_with_growth_signal_gets_draft(self) -> None:
        result = EnrichmentResult(
            enrichment_id="e2",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="GrowthCo",
            company_website="https://growthco.com",
            prospect_name="Maria Lopez",
            prospect_title="Head of Operations",
            b2b_fit=True,
            confidence_score=70,
            operational_pain_hypothesis="Manual onboarding is scaling poorly",
            possible_ai_use_case="AI onboarding assistant",
            evidence_items=[
                EvidenceItem(
                    claim="15 open ops roles",
                    source_type=EvidenceSourceType.CAREERS,
                    confidence=60,
                ),
                EvidenceItem(
                    claim="Fast-growing B2B startup",
                    source_type=EvidenceSourceType.WEBSITE,
                    confidence=65,
                ),
            ],
            risk_flags=["funding_round_announced"],
        )
        score = score_enrichment_result(result, lead_data={"country": "Colombia", "headcount": 15})
        assert score.recommended_action == RecommendedAction.DRAFT
        assert score.score >= 50
        assert any("growth" in r.lower() for r in score.score_reasons)

    def test_tier_b_buyer_with_good_evidence_gets_manual_research(self) -> None:
        result = EnrichmentResult(
            enrichment_id="e3",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="MidCo",
            company_website="https://midco.com",
            prospect_name="Carlos Ruiz",
            prospect_title="VP Engineering",
            b2b_fit=True,
            confidence_score=60,
            evidence_items=[
                EvidenceItem(
                    claim="SaaS product",
                    source_type=EvidenceSourceType.WEBSITE,
                    confidence=55,
                ),
            ],
        )
        score = score_enrichment_result(result, lead_data={"country": "Mexico", "headcount": 80})
        assert score.recommended_action == RecommendedAction.NEEDS_MANUAL_RESEARCH
        assert score.score >= 60
        assert any("tier B" in r for r in score.score_reasons)


class TestEnrichmentScoringNegativeCases:
    def test_b2c_puro_gets_discard(self) -> None:
        result = EnrichmentResult(
            enrichment_id="e4",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="Shopify Store",
            company_website="https://shop.com",
            prospect_name="Ana Gomez",
            prospect_title="CEO",
            b2b_fit=False,
            confidence_score=80,
            evidence_items=[
                EvidenceItem(
                    claim="E-commerce store",
                    source_type=EvidenceSourceType.WEBSITE,
                    confidence=70,
                ),
            ],
        )
        score = score_enrichment_result(
            result, lead_data={"country": "Argentina", "headcount": 200}
        )
        assert score.recommended_action == RecommendedAction.DISCARD
        assert score.score < 30
        assert any("B2C" in r for r in score.score_reasons)

    def test_microenterprise_gets_discard(self) -> None:
        result = EnrichmentResult(
            enrichment_id="e5",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="TinyCo",
            company_website="https://tinyco.com",
            prospect_name="Luis Diaz",
            prospect_title="Founder",
            b2b_fit=True,
            confidence_score=50,
            evidence_items=[
                EvidenceItem(
                    claim="Small consultancy",
                    source_type=EvidenceSourceType.WEBSITE,
                    confidence=50,
                ),
            ],
        )
        score = score_enrichment_result(result, lead_data={"country": "Chile", "headcount": 3})
        assert score.recommended_action == RecommendedAction.DISCARD
        assert score.score < 35
        assert any("microenterprise" in r.lower() for r in score.score_reasons)

    def test_junior_title_gets_manual_research_or_lower(self) -> None:
        result = EnrichmentResult(
            enrichment_id="e6",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="BigCo",
            company_website="https://bigco.com",
            prospect_name="Pedro Silva",
            prospect_title="Junior Analyst",
            b2b_fit=True,
            confidence_score=70,
            evidence_items=[
                EvidenceItem(
                    claim="Enterprise software",
                    source_type=EvidenceSourceType.WEBSITE,
                    confidence=65,
                ),
                EvidenceItem(
                    claim="Hiring support team",
                    source_type=EvidenceSourceType.CAREERS,
                    confidence=60,
                ),
            ],
        )
        score = score_enrichment_result(result, lead_data={"country": "Peru", "headcount": 120})
        assert score.recommended_action != RecommendedAction.DRAFT
        assert any("junior" in r.lower() for r in score.score_reasons)

    def test_no_evidence_gets_discard_or_wait(self) -> None:
        result = EnrichmentResult(
            enrichment_id="e7",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="MysteryCo",
            company_website=None,
            prospect_name="Unknown",
            prospect_title="CEO",
            b2b_fit=True,
            confidence_score=50,
            evidence_items=[],
        )
        score = score_enrichment_result(result, lead_data={"country": "Brazil", "headcount": 50})
        assert score.score < 50
        assert any("no evidence" in r.lower() for r in score.score_reasons)

    def test_outside_latam_with_weak_signals_gets_low_score(self) -> None:
        result = EnrichmentResult(
            enrichment_id="e8",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="USCo",
            company_website="https://usco.com",
            prospect_name="John Doe",
            prospect_title="COO",
            b2b_fit=True,
            confidence_score=70,
            evidence_items=[
                EvidenceItem(
                    claim="B2B platform",
                    source_type=EvidenceSourceType.WEBSITE,
                    confidence=60,
                ),
            ],
        )
        score = score_enrichment_result(
            result, lead_data={"country": "United States", "headcount": 80}
        )
        assert score.recommended_action != RecommendedAction.DRAFT
        assert score.score < 60

    def test_insufficient_data_risk_flag_reduces_score(self) -> None:
        result = EnrichmentResult(
            enrichment_id="e9",
            enrichment_status=EnrichmentStatus.INSUFFICIENT_DATA,
            company_name="WeakCo",
            company_website=None,
            b2b_fit=None,
            confidence_score=30,
            evidence_items=[],
            risk_flags=["insufficient_data"],
        )
        score = score_enrichment_result(result, lead_data={"country": "Argentina", "headcount": 30})
        assert score.score < 50
        assert any("insufficient data" in r.lower() for r in score.score_reasons)


class TestEnrichmentScoreBounds:
    def test_score_never_exceeds_100(self) -> None:
        result = EnrichmentResult(
            enrichment_id="e10",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="PerfectCo",
            company_website="https://perfect.com",
            prospect_title="Founder & CEO",
            b2b_fit=True,
            confidence_score=95,
            operational_pain_hypothesis="Pain",
            possible_ai_use_case="AI",
            evidence_items=[
                EvidenceItem(
                    claim="Hiring",
                    source_type=EvidenceSourceType.CAREERS,
                    confidence=90,
                ),
                EvidenceItem(
                    claim="B2B",
                    source_type=EvidenceSourceType.WEBSITE,
                    confidence=90,
                ),
                EvidenceItem(
                    claim="Blog",
                    source_type=EvidenceSourceType.BLOG,
                    confidence=90,
                ),
            ],
        )
        score = score_enrichment_result(result, lead_data={"country": "Mexico", "headcount": 100})
        assert 0 <= score.score <= 100
        assert 0 <= score.confidence_score <= 100

    def test_score_never_below_0(self) -> None:
        result = EnrichmentResult(
            enrichment_id="e11",
            enrichment_status=EnrichmentStatus.ENRICHED,
            company_name="BadCo",
            company_website=None,
            prospect_title="Intern",
            b2b_fit=False,
            confidence_score=10,
            evidence_items=[],
            risk_flags=["insufficient_data", "b2c_consumer"],
        )
        score = score_enrichment_result(result, lead_data={"country": "Spain", "headcount": 2})
        assert score.score == 0
        assert score.confidence_score == 0
        assert score.recommended_action == RecommendedAction.DISCARD


class TestScoringNodeIntegration:
    def test_score_node_updates_enrichment_result(self) -> None:
        from app.graph.enrichment_nodes import score_enrichment_node

        state = {
            "run_id": "r1",
            "lead_id": "l1",
            "lead": {
                "company_name": "Acme",
                "country": "Argentina",
                "headcount": 50,
                "prospect_title": "COO",
            },
            "enrichment_result": {
                "enrichment_id": "e1",
                "enrichment_status": "enriched",
                "company_name": "Acme",
                "b2b_fit": True,
                "confidence_score": 70,
                "recommended_action": "draft",
                "evidence_items": [
                    {
                        "claim": "Hiring ops",
                        "source_type": "careers",
                        "confidence": 70,
                    },
                    {
                        "claim": "B2B SaaS",
                        "source_type": "website",
                        "confidence": 80,
                    },
                ],
            },
        }
        result = score_enrichment_node(state)
        updated = result["enrichment_result"]
        assert updated["recommended_action"] == "draft"
        assert updated["confidence_score"] is not None
        flags = updated.get("risk_flags", [])
        assert any("score:" in f for f in flags)

    def test_score_node_skips_on_error(self) -> None:
        from app.graph.enrichment_nodes import score_enrichment_node

        state = {"status": "error", "error_message": "broken"}
        result = score_enrichment_node(state)
        assert result == {}

    def test_score_node_handles_invalid_result(self) -> None:
        from app.graph.enrichment_nodes import score_enrichment_node

        state = {
            "run_id": "r1",
            "lead_id": "l1",
            "lead": {"company_name": "Acme"},
            "enrichment_result": {"invalid": "data"},
        }
        result = score_enrichment_node(state)
        assert result == {}
