from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings, get_settings
from app.core.markets import country_market_status
from app.domain.candidates import CandidateStatus, SourceCandidate
from app.services.flexible_match import normalize_domain, title_fit_score


class ApolloEmailEnrichmentDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    should_enrich: bool
    score: int = Field(ge=0, le=100)
    reason: str
    confidence: int = Field(ge=0, le=100)
    missing_info: list[str] = Field(default_factory=list)
    guardrail_blocks: list[str] = Field(default_factory=list)
    estimated_credits: int = 0


class ApolloEmailEnrichmentPolicy:
    """Deterministic spend gate for Apollo person/email enrichment."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def evaluate(self, candidate: SourceCandidate) -> ApolloEmailEnrichmentDecision:
        blocks: list[str] = []
        missing: list[str] = []
        reasons: list[str] = []
        score = 0

        if candidate.prospect_email:
            blocks.append("prospect already has an email")
        if candidate.candidate_status == CandidateStatus.DUPLICATE:
            blocks.append("candidate is a duplicate")

        domain = normalize_domain(candidate.company_domain or candidate.company_website)
        if domain:
            score += 20
            reasons.append("company domain available")
        else:
            missing.append("company_domain")

        if candidate.prospect_name:
            score += 10
            reasons.append("prospect name available")
        else:
            missing.append("prospect_name")

        title_score, title_reason = title_fit_score(candidate.prospect_title)
        score += title_score
        reasons.append(title_reason)
        if title_score == 0:
            missing.append("buyer_title_signal")

        if candidate.prospect_linkedin_url:
            score += 10
            reasons.append("prospect LinkedIn available")

        if candidate.company_linkedin_url:
            score += 5
            reasons.append("company LinkedIn available")

        if candidate.candidate_score is not None:
            score += min(20, max(0, round(candidate.candidate_score / 5)))
            reasons.append(f"candidate score {candidate.candidate_score}")

        market_status = country_market_status(candidate.country)
        if market_status == "unsupported":
            blocks.append("unsupported country")
        elif market_status == "supported":
            score += 20
            reasons.append("supported Spanish-speaking high-ticket market")
        elif candidate.country:
            score -= 10
            reasons.append("country is not in supported market list")
        else:
            missing.append("country")

        score = max(0, min(score, 100))
        threshold = self.settings.apollo_email_enrichment_min_score
        should_enrich = not blocks and score >= threshold
        if not should_enrich and score < threshold:
            missing.append(f"score_below_{threshold}")

        reason = "; ".join(reasons + blocks) or "insufficient signal"
        confidence = min(95, max(30, score))
        return ApolloEmailEnrichmentDecision(
            should_enrich=should_enrich,
            score=score,
            reason=reason,
            confidence=confidence,
            missing_info=sorted(set(missing)),
            guardrail_blocks=blocks,
            estimated_credits=1 if should_enrich else 0,
        )
