from app.domain.enrichment import EnrichmentResult, EnrichmentStatus, RecommendedAction
from app.services.enrichment_review import apply_review_decision


def test_needs_review_blocks_draft_and_explains_role_transition() -> None:
    result = EnrichmentResult(
        enrichment_id="e1",
        enrichment_status=EnrichmentStatus.NEEDS_REVIEW,
        recommended_action=RecommendedAction.DRAFT,
        risk_flags=[
            "Current-role conflict: profile says COO but recent post says leaving day-to-day operations.",
        ],
    )

    updated = apply_review_decision(result)

    assert updated.review_required is True
    assert updated.review_category == "role_transition"
    assert updated.suggested_action == "pause"
    assert updated.recommended_action == RecommendedAction.NEEDS_MANUAL_RESEARCH
    assert "operational buyer" in (updated.review_summary or "")


def test_approve_exception_allows_reviewed_draft_action() -> None:
    result = EnrichmentResult(
        enrichment_id="e2",
        enrichment_status=EnrichmentStatus.NEEDS_REVIEW,
        recommended_action=RecommendedAction.DRAFT,
        user_decision="approve_exception",
        risk_flags=[
            "Prospect LinkedIn location is Fortaleza, Ceará, Brazil, while the lead country is Spain.",
        ],
    )

    updated = apply_review_decision(result)

    assert updated.review_required is True
    assert updated.review_category == "market_conflict"
    assert updated.recommended_action == RecommendedAction.DRAFT
