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
    assert assessment.signal_claim == (
        "tiene un help center and onboarding documentation for B2B clients"
    )
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


def test_draft_signal_blocks_hiring_trigger_without_operational_surface() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-3",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Vambe",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": (
                    "Vambe launched Operation 70: 70 new hires in 70 days, with roles "
                    "in Chile and Mexico and 50% of the goal completed"
                ),
                "source_type": "manual_context",
                "confidence": 90,
            }
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is False
    assert "operational signal" in assessment.reason


def test_draft_signal_prefers_operational_surface_over_hiring_trigger() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-4",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Vambe",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": (
                    "Vambe launched Operation 70: 70 new hires in 70 days, with roles "
                    "in Chile and Mexico"
                ),
                "source_type": "manual_context",
                "confidence": 90,
            },
            {
                "claim": (
                    "Vambe works with conversational AI workflows for sales, support, "
                    "CRM and WhatsApp in enterprise customer operations"
                ),
                "source_type": "manual_context",
                "confidence": 85,
            },
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is True
    assert assessment.signal_claim
    assert "conversational AI workflows" in assessment.signal_claim
    assert assessment.why_now_trigger
    assert "Operation 70" in assessment.why_now_trigger


def test_draft_signal_prefers_product_surface_over_soc_milestone() -> None:
    result = EnrichmentResult(
        enrichment_id="enr-5",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Bankingly",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=90,
        evidence_items=[
            {
                "claim": "Bankingly highlighted SOC 2 Type II / SOC 3 certification",
                "source_type": "manual_context",
                "confidence": 90,
            },
            {
                "claim": (
                    "Bankingly offers digital banking channels, digital onboarding, "
                    "loan origination and AI agents for banks and cooperatives"
                ),
                "source_type": "manual_context",
                "confidence": 85,
            },
        ],
    )

    assessment = assess_draft_signal(result)

    assert assessment.ready is True
    assert assessment.signal_claim
    assert "digital banking channels" in assessment.signal_claim
    assert "SOC 2" not in assessment.signal_claim
