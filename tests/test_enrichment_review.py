from app.domain.enrichment import EnrichmentResult, EnrichmentStatus, RecommendedAction
from app.services.enrichment_review import apply_review_decision


def test_needs_review_blocks_draft_and_explains_role_transition() -> None:
    result = EnrichmentResult(
        enrichment_id="e1",
        enrichment_status=EnrichmentStatus.NEEDS_REVIEW,
        recommended_action=RecommendedAction.DRAFT,
        risk_flags=[
            (
                "Current-role conflict: profile says COO but recent post says leaving "
                "day-to-day operations."
            ),
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
            (
                "Prospect LinkedIn location is Fortaleza, Ceara, Brazil, while the "
                "lead country is Spain."
            ),
        ],
    )

    updated = apply_review_decision(result)

    assert updated.review_required is True
    assert updated.review_category == "market_conflict"
    assert updated.recommended_action == RecommendedAction.DRAFT


def test_positive_headcount_signal_does_not_force_review() -> None:
    result = EnrichmentResult(
        enrichment_id="e3",
        enrichment_status=EnrichmentStatus.ENRICHED,
        recommended_action=RecommendedAction.DRAFT,
        risk_flags=[
            "headcount in ICP range (20-200)",
            "company website present",
            "prospect is tier B buyer",
        ],
    )

    updated = apply_review_decision(result)

    assert updated.review_required is False
    assert updated.recommended_action == RecommendedAction.DRAFT


def test_supported_market_with_brazil_caution_does_not_force_review() -> None:
    result = EnrichmentResult(
        enrichment_id="e4",
        enrichment_status=EnrichmentStatus.ENRICHED,
        country="Chile",
        recommended_action=RecommendedAction.DRAFT,
        risk_flags=[
            (
                "Brazil appears in public/company context, but focus outreach on "
                "Chile/Mexico Spanish-speaking operations."
            ),
            "confirmed B2B fit",
        ],
    )

    updated = apply_review_decision(result)

    assert updated.review_required is False
    assert updated.recommended_action == RecommendedAction.DRAFT


def test_linkedin_identity_caution_does_not_force_review() -> None:
    result = EnrichmentResult(
        enrichment_id="e6",
        enrichment_status=EnrichmentStatus.ENRICHED,
        recommended_action=RecommendedAction.DRAFT,
        risk_flags=[
            (
                "Person and company claims are largely from pasted LinkedIn context; "
                "avoid treating similarly named web results as identity proof."
            ),
        ],
    )

    updated = apply_review_decision(result)

    assert updated.review_required is False
    assert updated.recommended_action == RecommendedAction.DRAFT


def test_positive_buyer_tier_signal_does_not_force_review() -> None:
    result = EnrichmentResult(
        enrichment_id="e7",
        enrichment_status=EnrichmentStatus.ENRICHED,
        recommended_action=RecommendedAction.DRAFT,
        risk_flags=[
            "prospect is tier B buyer",
            "operational pain hypothesis identified",
        ],
    )

    updated = apply_review_decision(result)

    assert updated.review_required is False
    assert updated.recommended_action == RecommendedAction.DRAFT


def test_explicit_unclear_authority_still_forces_review() -> None:
    result = EnrichmentResult(
        enrichment_id="e8",
        enrichment_status=EnrichmentStatus.ENRICHED,
        recommended_action=RecommendedAction.DRAFT,
        risk_flags=[
            "Unclear authority: person may not have enough authority for a USD 5k-10k project.",
        ],
    )

    updated = apply_review_decision(result)

    assert updated.review_required is True
    assert updated.review_category == "unclear_buyer_authority"
    assert updated.recommended_action == RecommendedAction.NEEDS_MANUAL_RESEARCH


def test_explicit_company_size_conflict_still_forces_review() -> None:
    result = EnrichmentResult(
        enrichment_id="e5",
        enrichment_status=EnrichmentStatus.ENRICHED,
        recommended_action=RecommendedAction.DRAFT,
        risk_flags=[
            (
                "Company size is inconsistent: user provided 310, LinkedIn context "
                "says 51-200 employees."
            ),
        ],
    )

    updated = apply_review_decision(result)

    assert updated.review_required is True
    assert updated.review_category == "company_size_conflict"
    assert updated.recommended_action == RecommendedAction.NEEDS_MANUAL_RESEARCH
