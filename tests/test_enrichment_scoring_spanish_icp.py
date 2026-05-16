from app.domain.enrichment import EnrichmentResult, EvidenceItem, RecommendedAction
from app.services.enrichment_scoring import score_enrichment_result


def _result() -> EnrichmentResult:
    return EnrichmentResult(
        enrichment_id="enr-1",
        company_name="Acme",
        company_website="https://acme.com",
        b2b_fit=True,
        operational_pain_hypothesis="Scaling operations",
        possible_ai_use_case="Automate revenue workflows",
        confidence_score=80,
        evidence_items=[
            EvidenceItem(
                claim="Acme sells B2B software",
                source_type="website",
                source_url="https://acme.com",
                confidence=70,
                used_in_message=True,
            ),
            EvidenceItem(
                claim="Acme uses HubSpot",
                source_type="website",
                source_url="https://acme.com",
                confidence=70,
                used_in_message=True,
            ),
        ],
    )


def test_supported_spanish_country_can_score_to_draft() -> None:
    score = score_enrichment_result(
        _result(),
        lead_data={"country": "Mexico", "prospect_title": "COO", "headcount": 50},
    )

    assert score.score >= 80
    assert score.recommended_action == RecommendedAction.DRAFT
    assert "country is supported Spanish-speaking ICP" in score.score_reasons


def test_brazil_is_discarded_by_score() -> None:
    score = score_enrichment_result(
        _result(),
        lead_data={"country": "Brazil", "prospect_title": "COO", "headcount": 50},
    )

    assert score.recommended_action == RecommendedAction.DISCARD
    assert "country is unsupported" in score.score_reasons


def test_out_of_scope_country_is_penalized() -> None:
    score = score_enrichment_result(
        _result(),
        lead_data={"country": "Germany", "prospect_title": "COO", "headcount": 50},
    )

    assert score.score < 80
    assert score.recommended_action != RecommendedAction.DRAFT
