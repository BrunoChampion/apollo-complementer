import pytest
from pydantic import ValidationError

from app.domain.enrichment import (
    EnrichmentResult,
    EnrichmentStatus,
    EvidenceItem,
    EvidenceSourceType,
    RecommendedAction,
)


def test_enrichment_result_validates_required_fields() -> None:
    result = EnrichmentResult.model_validate(
        {
            "enrichment_id": "enrich_001",
            "lead_id": "lead_001",
            "company_name": "Andes ERP Partners",
            "enrichment_status": "pending",
            "recommended_action": "draft",
        }
    )
    assert result.enrichment_id == "enrich_001"
    assert result.enrichment_status is EnrichmentStatus.PENDING
    assert result.recommended_action is RecommendedAction.DRAFT
    assert result.evidence_count == 0


def test_invalid_enrichment_status_fails() -> None:
    with pytest.raises(ValidationError):
        EnrichmentResult.model_validate(
            {
                "enrichment_id": "enrich_002",
                "enrichment_status": "completed",
            }
        )


def test_invalid_recommended_action_fails() -> None:
    with pytest.raises(ValidationError):
        EnrichmentResult.model_validate(
            {
                "enrichment_id": "enrich_003",
                "recommended_action": "spam",
            }
        )


def test_evidence_item_validates_required_fields() -> None:
    item = EvidenceItem.model_validate(
        {
            "claim": "Company has 50 employees",
            "source_type": "website",
            "source_url": "https://example.com/about",
            "confidence": 85,
        }
    )
    assert item.claim == "Company has 50 employees"
    assert item.source_type is EvidenceSourceType.WEBSITE
    assert item.confidence == 85


def test_evidence_item_blank_claim_fails() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem.model_validate(
            {
                "claim": "   ",
                "source_type": "blog",
            }
        )


def test_evidence_item_default_source_type() -> None:
    item = EvidenceItem.model_validate({"claim": "Hiring 5 support reps"})
    assert item.source_type is EvidenceSourceType.UNKNOWN
    assert item.confidence == 50


def test_enrichment_result_computes_evidence_count() -> None:
    result = EnrichmentResult.model_validate(
        {
            "enrichment_id": "enrich_004",
            "evidence_items": [
                {"claim": "Signal A", "source_type": "website"},
                {"claim": "Signal B", "source_type": "careers"},
                {"claim": "Signal C", "source_type": "website"},
            ],
        }
    )
    assert result.evidence_count == 3
    assert result.evidence_sources == ["careers", "website"]


def test_enrichment_result_blank_strings_become_none() -> None:
    result = EnrichmentResult.model_validate(
        {
            "enrichment_id": "enrich_005",
            "company_summary": "   ",
            "operational_pain_hypothesis": "Slow onboarding",
        }
    )
    assert result.company_summary is None
    assert result.operational_pain_hypothesis == "Slow onboarding"


def test_enrichment_result_confidence_score_bounds() -> None:
    with pytest.raises(ValidationError):
        EnrichmentResult.model_validate(
            {
                "enrichment_id": "enrich_006",
                "confidence_score": 150,
            }
        )

    with pytest.raises(ValidationError):
        EnrichmentResult.model_validate(
            {
                "enrichment_id": "enrich_007",
                "confidence_score": -5,
            }
        )


def test_evidence_item_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem.model_validate(
            {
                "claim": "Test",
                "confidence": 101,
            }
        )

    with pytest.raises(ValidationError):
        EvidenceItem.model_validate(
            {
                "claim": "Test",
                "confidence": -1,
            }
        )


def test_enrichment_enums_expected_values() -> None:
    assert EnrichmentStatus.PENDING == "pending"
    assert EnrichmentStatus.RUNNING == "running"
    assert EnrichmentStatus.ENRICHED == "enriched"
    assert EnrichmentStatus.NEEDS_REVIEW == "needs_review"
    assert EnrichmentStatus.INSUFFICIENT_DATA == "insufficient_data"
    assert EnrichmentStatus.FAILED == "failed"

    assert RecommendedAction.DRAFT == "draft"
    assert RecommendedAction.NEEDS_MANUAL_RESEARCH == "needs_manual_research"
    assert RecommendedAction.NEEDS_EMAIL_VERIFICATION == "needs_email_verification"
    assert RecommendedAction.DISCARD == "discard"
    assert RecommendedAction.WAIT == "wait"

    assert EvidenceSourceType.WEBSITE == "website"
    assert EvidenceSourceType.CAREERS == "careers"
    assert EvidenceSourceType.HELP_CENTER == "help_center"
    assert EvidenceSourceType.BLOG == "blog"
    assert EvidenceSourceType.APOLLO == "apollo"
    assert EvidenceSourceType.MANUAL_CONTEXT == "manual_context"
    assert EvidenceSourceType.SEARCH_RESULT == "search_result"
    assert EvidenceSourceType.UNKNOWN == "unknown"
