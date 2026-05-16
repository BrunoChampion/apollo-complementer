from app.domain.enrichment import EnrichmentResult, EnrichmentStatus, RecommendedAction
from app.services.draft_signal import assess_draft_signal


def test_draft_signal_accepts_operational_evidence() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-1",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Acme",
        operational_pain_hypothesis=(
            "el conocimiento queda repartido entre documentación, soporte y onboarding"
        ),
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": "Acme has a help center and onboarding documentation for B2B clients",
                "source_type": "help_center",
                "confidence": 90,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is True
    assert assessment.signal_claim == "tiene un help center and onboarding documentation for B2B clients"
    assert "documentación" in (assessment.friction_hypothesis or "")


def test_draft_signal_blocks_decorative_evidence() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-2",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Acme",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": "Acme has an office in Mexico",
                "source_type": "website",
                "confidence": 90,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is False
    assert "operational signal" in assessment.reason
