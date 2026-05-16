from __future__ import annotations

from dataclasses import dataclass

from app.domain.enrichment import EnrichmentResult, EnrichmentStatus, RecommendedAction

APPROVE_EXCEPTION = "approve_exception"


@dataclass(frozen=True)
class ReviewDecision:
    review_required: bool
    review_category: str | None = None
    review_summary: str | None = None
    review_evidence: str | None = None
    suggested_action: str | None = None
    suggested_action_reason: str | None = None

    def as_update(self) -> dict[str, object]:
        return {
            "review_required": self.review_required,
            "review_category": self.review_category,
            "review_summary": self.review_summary,
            "review_evidence": self.review_evidence,
            "suggested_action": self.suggested_action,
            "suggested_action_reason": self.suggested_action_reason,
        }


def apply_review_decision(result: EnrichmentResult) -> EnrichmentResult:
    decision = build_review_decision(result)
    result.review_required = decision.review_required
    result.review_category = decision.review_category
    result.review_summary = decision.review_summary
    result.review_evidence = decision.review_evidence
    result.suggested_action = decision.suggested_action
    result.suggested_action_reason = decision.suggested_action_reason

    if (
        decision.review_required
        and result.user_decision != APPROVE_EXCEPTION
        and result.recommended_action != RecommendedAction.DISCARD
    ):
        result.recommended_action = RecommendedAction.NEEDS_MANUAL_RESEARCH
    return result


def build_review_decision(result: EnrichmentResult) -> ReviewDecision:
    flags = result.risk_flags or []
    risk_text = " ".join(flags).lower()

    if result.enrichment_status == EnrichmentStatus.NEEDS_REVIEW:
        category = _category_from_risk_text(risk_text)
        return _decision_for_category(category, flags, result)

    category = _category_from_risk_text(risk_text)
    if category:
        return _decision_for_category(category, flags, result)

    return ReviewDecision(review_required=False)


def _category_from_risk_text(risk_text: str) -> str | None:
    if any(
        term in risk_text
        for term in (
            "current-role conflict",
            "leaving",
            "new role",
            "advisor",
            "day-to-day",
        )
    ):
        return "role_transition"
    if any(
        term in risk_text
        for term in (
            "location is",
            "market/language",
            "market conflict",
            "unsupported country",
            "unsupported_country",
        )
    ):
        return "market_conflict"
    if any(
        term in risk_text
        for term in (
            "company-size conflict",
            "company size conflict",
            "company above 200 employees needs strong exception",
            "company size is inconsistent",
            "company size signals conflict",
        )
    ):
        return "company_size_conflict"
    if any(
        term in risk_text
        for term in (
            "identity conflict",
            "same person conflict",
            "different person",
            "different company",
            "may refer to a different",
        )
    ):
        return "identity_conflict"
    if any(
        term in risk_text
        for term in (
            "unclear buyer",
            "unclear authority",
            "no clear authority",
            "not a decision maker",
            "not decision maker",
            "may not have enough authority",
            "insufficient authority",
            "low authority",
        )
    ):
        return "unclear_buyer_authority"
    return None


def _decision_for_category(
    category: str | None,
    flags: list[str],
    result: EnrichmentResult,
) -> ReviewDecision:
    evidence = _human_evidence(flags)
    if category == "role_transition":
        return ReviewDecision(
            review_required=True,
            review_category=category,
            review_summary=(
                "The prospect may no longer be the right operational buyer for this "
                "company, so a draft could target the wrong role or company context."
            ),
            review_evidence=evidence,
            suggested_action="pause",
            suggested_action_reason=(
                "Pause until you decide whether to target the current company, the new "
                "company/role, or treat this as a relationship-only connection."
            ),
        )
    if category == "market_conflict":
        return ReviewDecision(
            review_required=True,
            review_category=category,
            review_summary=(
                "The company may fit the ICP, but the prospect/market signal is ambiguous "
                "for the current Spanish-speaking ICP."
            ),
            review_evidence=evidence,
            suggested_action="approve_exception",
            suggested_action_reason=(
                "Continue only if you explicitly accept the exception and the outreach "
                "will be framed around the company operation, not an unsupported market."
            ),
        )
    if category == "company_size_conflict":
        return ReviewDecision(
            review_required=True,
            review_category=category,
            review_summary=(
                "The company size signals conflict, so budget/fit should not be assumed."
            ),
            review_evidence=evidence,
            suggested_action="needs_more_context",
            suggested_action_reason=(
                "Clarify or accept the size uncertainty before using headcount as part "
                "of the outreach rationale."
            ),
        )
    if category == "identity_conflict":
        return ReviewDecision(
            review_required=True,
            review_category=category,
            review_summary=(
                "The available evidence may refer to a different person or company than "
                "the exported lead."
            ),
            review_evidence=evidence,
            suggested_action="discard",
            suggested_action_reason=(
                "Discard or fix the lead data unless the identity match can be confirmed "
                "from the pasted LinkedIn profile."
            ),
        )
    if category == "unclear_buyer_authority":
        return ReviewDecision(
            review_required=True,
            review_category=category,
            review_summary="The person may not have enough authority for a USD 5k-10k project.",
            review_evidence=evidence,
            suggested_action="change_target",
            suggested_action_reason=(
                "Find a founder, COO, CTO, or senior operator at the same account before drafting."
            ),
        )

    return ReviewDecision(
        review_required=True,
        review_category="manual_exception_required",
        review_summary=(
            "The agent found useful evidence, but also flagged uncertainty that should "
            "not be resolved automatically."
        ),
        review_evidence=evidence or (result.trigger_summary or result.company_summary),
        suggested_action="needs_more_context",
        suggested_action_reason=(
            "Review the flagged uncertainty and either pause, discard, change target, "
            "or approve an explicit exception."
        ),
    )


def _human_evidence(flags: list[str]) -> str | None:
    useful = [
        flag
        for flag in flags
        if flag
        and not flag.startswith("score:")
        and flag
        not in {
            "baseline interest",
            "confirmed B2B fit",
            "company website present",
            "multiple evidence items",
            "operational pain hypothesis identified",
            "possible AI use case identified",
            "multiple evidence sources boost confidence",
        }
        and "country is supported" not in flag.lower()
        and "country is latam" not in flag.lower()
        and "prospect is tier" not in flag.lower()
        and "headcount in icp range" not in flag.lower()
    ]
    if not useful:
        return None
    return " | ".join(useful[:4])
