from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.markets import country_market_status
from app.domain.enrichment import EnrichmentResult, RecommendedAction

LATAM_COUNTRIES = {"argentina", "colombia", "mexico", "chile", "peru", "brasil", "brazil"}

TIER_A_TITLES = {
    "founder",
    "ceo",
    "coo",
    "cto",
    "co-founder",
    "cofounder",
    "president",
}
TIER_B_TITLES = {
    "head of operations",
    "director of operations",
    "head of customer success",
    "head of support",
    "vp engineering",
    "vp product",
    "head of technology",
    "director of customer success",
    "director of support",
    "vp operations",
    "vp customer success",
    "vp of engineering",
    "vp of product",
    "director of engineering",
    "chief technology officer",
    "chief operating officer",
}
TIER_C_TITLES = {
    "product manager",
    "customer support manager",
    "operations manager",
    "sales director",
    "commercial manager",
    "implementation manager",
    "customer success manager",
}

JUNIOR_TITLES = {
    "junior",
    "jr",
    "trainee",
    "intern",
    "assistant",
    "coordinator",
    "specialist",
    "analyst",
}

MIN_DRAFT_SCORE = 80
MIN_DRAFT_EVIDENCE = 2
MIN_DRAFT_CONFIDENCE = 65
MIN_RESEARCH_SCORE = 60
MIN_WAIT_SCORE = 35


@dataclass(frozen=True)
class EnrichmentScore:
    score: int
    confidence_score: int
    recommended_action: RecommendedAction
    score_reasons: list[str]


def _normalize(text: str | None) -> str:
    return (text or "").lower().strip()


def _prospect_tier_score(title: str | None) -> tuple[int, str | None]:
    t = _normalize(title)
    if not t:
        return 0, None
    if any(a in t for a in TIER_A_TITLES):
        return 15, "prospect is tier A buyer"
    if any(b in t for b in TIER_B_TITLES):
        return 10, "prospect is tier B buyer"
    if any(c in t for c in TIER_C_TITLES):
        return 5, "prospect is tier C buyer"
    if any(j in t for j in JUNIOR_TITLES):
        return -30, "prospect title is junior/trainee"
    return 0, None


def _country_score(country: str | None) -> tuple[int, str | None]:
    status = country_market_status(country)
    if status == "unsupported":
        return -100, "country is unsupported"
    if status == "supported":
        return 15, "country is supported Spanish-speaking ICP"
    if status == "out_of_scope":
        return -30, "country is outside Spanish-speaking ICP"
    c = _normalize(country)
    if not c:
        return 0, None
    if c in LATAM_COUNTRIES:
        return 15, "country is LATAM"
    return -20, "country is outside LATAM"


def _headcount_score(headcount: int | None, risk_flags: list[str]) -> tuple[int, str | None]:
    if headcount is None:
        return -5, "headcount/company_size unknown"
    if 10 <= headcount <= 19:
        has_growth = any(
            signal in " ".join(risk_flags).lower()
            for signal in ("funding", "growth", "hiring", "expansion")
        )
        if has_growth:
            return 10, "headcount 10-19 with growth signals"
        return 0, "headcount 10-19 without clear growth signal"
    if 20 <= headcount <= 200:
        return 10, "headcount in ICP range (20-200)"
    if headcount < 5:
        return -50, "microenterprise (<5 employees)"
    if headcount < 10:
        return -30, "company under 10 employees"
    if headcount > 500:
        return -25, "very large enterprise (>500)"
    if headcount > 200:
        return -10, "company above 200 employees needs strong exception"
    return 0, None


def _parse_headcount(lead_data: dict[str, Any]) -> int | None:
    explicit = lead_data.get("headcount")
    if isinstance(explicit, int):
        return explicit
    if isinstance(explicit, str) and explicit.strip().isdigit():
        return int(explicit.strip())
    raw = lead_data.get("company_size") or lead_data.get("employees")
    if raw is None:
        return None
    text = str(raw).lower().replace(",", "")
    numbers = [int(match) for match in re.findall(r"\d{1,5}", text)]
    if not numbers:
        return None
    return max(numbers)


def _b2b_score(b2b_fit: bool | None) -> tuple[int, str | None]:
    if b2b_fit is True:
        return 20, "confirmed B2B fit"
    if b2b_fit is False:
        return -50, "B2C or non-B2B business model"
    return 0, "B2B fit unknown"


def score_enrichment_result(
    result: EnrichmentResult,
    lead_data: dict[str, Any] | None = None,
) -> EnrichmentScore:
    lead_data = lead_data or {}
    score = 25
    reasons: list[str] = ["baseline interest"]

    # Company fit
    delta, reason = _b2b_score(result.b2b_fit)
    score += delta
    if reason:
        reasons.append(reason)

    # Geography
    delta, reason = _country_score(lead_data.get("country"))
    score += delta
    if reason:
        reasons.append(reason)
        if (
            reason == "country is supported Spanish-speaking ICP"
            and _normalize(lead_data.get("country")) in LATAM_COUNTRIES
        ):
            reasons.append("country is LATAM")

    # Headcount
    delta, reason = _headcount_score(_parse_headcount(lead_data), result.risk_flags or [])
    score += delta
    if reason:
        reasons.append(reason)

    # Website presence
    if result.company_website or lead_data.get("company_website"):
        score += 5
        reasons.append("company website present")
    else:
        score -= 15
        reasons.append("no company website")

    # Prospect title tier
    prospect_title = result.prospect_title or lead_data.get("prospect_title")
    delta, reason = _prospect_tier_score(prospect_title)
    score += delta
    if reason:
        reasons.append(reason)

    # Evidence
    evidence_count = len(result.evidence_items or [])
    if evidence_count >= 2:
        score += 10
        reasons.append("multiple evidence items")
    elif evidence_count == 1:
        score += 3
        reasons.append("single evidence item")
    else:
        score -= 25
        reasons.append("no evidence items")

    # Enrichment depth
    if result.operational_pain_hypothesis:
        score += 5
        reasons.append("operational pain hypothesis identified")
    if result.possible_ai_use_case:
        score += 5
        reasons.append("possible AI use case identified")

    # Risk flags
    risk_lower = " ".join(result.risk_flags or []).lower()
    if "insufficient_data" in risk_lower:
        score -= 15
        reasons.append("insufficient data risk flag")
    if any(r in risk_lower for r in ("b2c", "consumer", "retail")):
        score -= 20
        reasons.append("B2C/consumer risk flag")

    # Cap score
    score = max(0, min(100, score))

    # Confidence scoring
    base_confidence = result.confidence_score or 50
    confidence = base_confidence
    if evidence_count >= 2:
        unique_sources = {item.source_type.value for item in (result.evidence_items or [])}
        if len(unique_sources) >= 2:
            confidence += 10
            reasons.append("multiple evidence sources boost confidence")
    if evidence_count == 0:
        confidence -= 20
        reasons.append("missing evidence reduces confidence")
    elif evidence_count == 1:
        confidence -= 5
    confidence = max(0, min(100, confidence))

    # Recommended action
    recommended_action = _select_action(score, evidence_count, confidence)

    return EnrichmentScore(
        score=score,
        confidence_score=confidence,
        recommended_action=recommended_action,
        score_reasons=reasons,
    )


def _select_action(score: int, evidence_count: int, confidence: int) -> RecommendedAction:
    if (
        score >= MIN_DRAFT_SCORE
        and evidence_count >= MIN_DRAFT_EVIDENCE
        and confidence >= MIN_DRAFT_CONFIDENCE
    ):
        return RecommendedAction.DRAFT
    if score >= MIN_RESEARCH_SCORE and evidence_count >= 1:
        return RecommendedAction.NEEDS_MANUAL_RESEARCH
    if score >= MIN_WAIT_SCORE:
        return RecommendedAction.NEEDS_EMAIL_VERIFICATION
    return RecommendedAction.DISCARD
