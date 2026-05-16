from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.core.markets import country_market_status
from app.domain.candidates import SourceCandidate
from app.domain.leads import LeadRow
from app.services.flexible_match import normalize_text, title_fit_score


class ProspectRecord(Protocol):
    company_name: str
    company_linkedin_url: str | None
    prospect_name: str | None
    prospect_title: str | None
    prospect_linkedin_url: str | None
    country: str | None
    industry: str | None
    company_size: str | None
    manual_company_linkedin_text: str | None
    manual_person_linkedin_text: str | None
    annual_revenue: str | None
    total_funding: str | None
    latest_funding: str | None
    latest_funding_amount: str | None


@dataclass(frozen=True)
class ReadinessResult:
    identity_validation_status: str
    identity_validation_reason: str
    icp_status: str
    icp_score: int
    icp_score_reason: str
    ready_for_enrichment: bool
    ready_for_draft: bool = False

    def as_update(self) -> dict[str, object]:
        return {
            "identity_validation_status": self.identity_validation_status,
            "identity_validation_reason": self.identity_validation_reason,
            "icp_status": self.icp_status,
            "icp_score": self.icp_score,
            "icp_score_reason": self.icp_score_reason,
            "ready_for_enrichment": self.ready_for_enrichment,
            "ready_for_draft": self.ready_for_draft,
        }


def validate_readiness(record: LeadRow | SourceCandidate) -> ReadinessResult:
    if country_market_status(record.country) == "unsupported":
        return ReadinessResult(
            identity_validation_status="blocked_unsupported_country",
            identity_validation_reason="Country is outside the supported ICP markets.",
            icp_status="disqualified",
            icp_score=0,
            icp_score_reason="unsupported country",
            ready_for_enrichment=False,
        )

    missing = _missing_required_context(record)
    if missing:
        return ReadinessResult(
            identity_validation_status="missing_required_context",
            identity_validation_reason="Missing required fields: " + ", ".join(missing),
            icp_status="not_evaluated",
            icp_score=0,
            icp_score_reason="ICP not evaluated until required LinkedIn URLs and pasted LinkedIn content are present.",
            ready_for_enrichment=False,
        )

    identity_status, identity_reason = _validate_identity(record)
    icp_status, icp_score, icp_reason = _score_icp(record)
    ready = identity_status == "valid" and icp_status == "qualified"
    return ReadinessResult(
        identity_validation_status=identity_status,
        identity_validation_reason=identity_reason,
        icp_status=icp_status,
        icp_score=icp_score,
        icp_score_reason=icp_reason,
        ready_for_enrichment=ready,
    )


def readiness_block_reason(record: LeadRow | SourceCandidate) -> str | None:
    result = validate_readiness(record)
    if result.ready_for_enrichment:
        return None
    return (
        f"{result.identity_validation_status}: {result.identity_validation_reason}; "
        f"{result.icp_status}: {result.icp_score_reason}"
    )


def _missing_required_context(record: LeadRow | SourceCandidate) -> list[str]:
    missing: list[str] = []
    required = {
        "company_linkedin_url": record.company_linkedin_url,
        "prospect_linkedin_url": record.prospect_linkedin_url,
        "manual_company_linkedin_text": record.manual_company_linkedin_text,
        "manual_person_linkedin_text": record.manual_person_linkedin_text,
    }
    for field, value in required.items():
        if not str(value or "").strip():
            missing.append(field)
    return missing


def _validate_identity(record: LeadRow | SourceCandidate) -> tuple[str, str]:
    person_text = normalize_text(record.manual_person_linkedin_text)
    company_text = normalize_text(record.manual_company_linkedin_text)

    company_match = _name_present(record.company_name, company_text)
    if not company_match:
        return (
            "identity_conflict",
            "Pasted company LinkedIn text does not clearly contain the exported company name.",
        )

    if not record.prospect_name:
        return (
            "needs_manual_review",
            "Prospect name is missing, so the person LinkedIn text cannot be matched to the Apollo export.",
        )

    person_match = _name_present(record.prospect_name, person_text)
    if not person_match:
        return (
            "identity_conflict",
            "Pasted person LinkedIn text does not clearly contain the exported prospect name.",
        )

    return (
        "valid",
        "Required LinkedIn URLs and pasted LinkedIn content are present, and names match the exported Apollo record.",
    )


def _score_icp(record: LeadRow | SourceCandidate) -> tuple[str, int, str]:
    score = 0
    reasons: list[str] = []
    hard_disqualifiers: list[str] = []
    manual_review_flags: list[str] = []

    market_status = country_market_status(record.country)
    if market_status == "unsupported":
        hard_disqualifiers.append("unsupported country")
    elif market_status == "supported":
        score += 15
        reasons.append("supported Spanish-speaking market")
    elif record.country:
        manual_review_flags.append("country is outside the primary market list")
    else:
        manual_review_flags.append("country is missing")

    headcount = _extract_headcount(record)
    if headcount is None:
        manual_review_flags.append("company_size/headcount is unknown")
    else:
        low, high = headcount
        if high < 10:
            hard_disqualifiers.append("company appears to have fewer than 10 employees")
        elif low <= 14 and not _has_budget_or_growth_signal(record):
            score += 8
            manual_review_flags.append("10-14 employees without a clear budget or growth signal")
        elif 10 <= low and high <= 200:
            score += 20 if high <= 100 else 16
            reasons.append("headcount is inside the 10-200 ICP range")
        elif high > 500:
            hard_disqualifiers.append("company appears too large for the current ICP")
        else:
            score += 5
            manual_review_flags.append("company is above 200 employees and needs a strong exception")

    combined = _combined_context(record)
    if _has_b2c_risk(combined) and not _has_b2b_signal(combined):
        hard_disqualifiers.append("B2C/consumer signals without a clear B2B motion")
    elif _has_b2b_signal(combined):
        score += 20
        reasons.append("B2B or professional-services motion is visible")
    else:
        manual_review_flags.append("B2B fit is not explicit")

    if _has_operational_pain_signal(combined):
        score += 20
        reasons.append("operational/support/knowledge-work pain signal is visible")
    else:
        manual_review_flags.append("no clear operational pain signal yet")

    title_score, title_reason = title_fit_score(record.prospect_title)
    if title_score:
        score += min(20, title_score)
        reasons.append(title_reason)
    else:
        manual_review_flags.append("buyer title is not clearly mapped to a decision maker")

    if _has_budget_or_growth_signal(record):
        score += 10
        reasons.append("budget, funding, revenue, hiring, or growth signal is visible")

    score = max(0, min(score, 100))
    if hard_disqualifiers:
        return "disqualified", min(score, 30), "; ".join(hard_disqualifiers)
    if score >= 65 and not manual_review_flags:
        return "qualified", score, "; ".join(reasons)
    if score >= 50:
        return (
            "needs_manual_review",
            score,
            "; ".join(reasons + manual_review_flags),
        )
    return "disqualified", score, "; ".join(reasons + manual_review_flags)


def _name_present(name: str | None, text: str) -> bool:
    normalized_name = normalize_text(name)
    if not normalized_name or not text:
        return False
    if normalized_name in text:
        return True
    legal_suffixes = {
        "inc",
        "llc",
        "ltd",
        "corp",
        "co",
        "sa",
        "sac",
        "srl",
        "spa",
        "sas",
        "gmbh",
    }
    tokens = [
        token
        for token in normalized_name.split()
        if len(token) >= 3 and token not in legal_suffixes
    ]
    if len(tokens) <= 1:
        return bool(tokens and tokens[0] in text)
    return all(token in text for token in tokens)


def _combined_context(record: LeadRow | SourceCandidate) -> str:
    parts = [
        record.company_name,
        record.prospect_title,
        record.country,
        record.industry,
        record.company_size,
        getattr(record, "technologies", None),
        getattr(record, "raw_headline", None),
        getattr(record, "raw_company_description", None),
        getattr(record, "manual_context", None),
        getattr(record, "manual_company_context", None),
        getattr(record, "manual_person_context", None),
        getattr(record, "manual_linkedin_notes", None),
        record.manual_company_linkedin_text,
        record.manual_person_linkedin_text,
        getattr(record, "annual_revenue", None),
        getattr(record, "total_funding", None),
        getattr(record, "latest_funding", None),
        getattr(record, "latest_funding_amount", None),
    ]
    return normalize_text(" ".join(str(part) for part in parts if part))


def _extract_headcount(record: LeadRow | SourceCandidate) -> tuple[int, int] | None:
    company_size = str(record.company_size or "").strip().replace(",", "")
    if company_size.isdigit():
        value = int(company_size)
        return (value, value)

    source = " ".join(
        str(part)
        for part in [
            record.company_size,
            record.manual_company_linkedin_text,
            getattr(record, "manual_company_context", None),
        ]
        if part
    )
    text = normalize_text(source).replace(",", "")
    if not text:
        return None

    range_match = re.search(r"(\d{1,5})\s*(?:-|–|a|to)\s*(\d{1,5})", text)
    if range_match:
        low = int(range_match.group(1))
        high = int(range_match.group(2))
        return (min(low, high), max(low, high))

    single_match = re.search(r"(\d{1,5})\s*(?:empleados|employees|personas|people)", text)
    if single_match:
        value = int(single_match.group(1))
        return (value, value)

    if text.strip().isdigit():
        value = int(text.strip())
        return (value, value)

    return None


def _has_b2b_signal(text: str) -> bool:
    signals = (
        "b2b",
        "saas",
        "software",
        "plataforma",
        "platform",
        "empresas",
        "enterprise",
        "clientes corporativos",
        "servicios profesionales",
        "consultoria",
        "consulting",
        "fintech",
        "hr tech",
        "rrhh",
        "cybersecurity",
        "ciberseguridad",
        "erp",
    )
    return any(signal in text for signal in signals)


def _has_b2c_risk(text: str) -> bool:
    risks = (
        "b2c",
        "consumer",
        "consumidor",
        "ecommerce",
        "e-commerce",
        "retail",
        "tienda",
        "restaurante",
        "moda",
    )
    return any(risk in text for risk in risks)


def _has_operational_pain_signal(text: str) -> bool:
    signals = (
        "soporte",
        "support",
        "customer success",
        "clientes",
        "tickets",
        "onboarding",
        "implementacion",
        "implementation",
        "operaciones",
        "operations",
        "documentacion",
        "documentation",
        "docs",
        "knowledge base",
        "base de conocimiento",
        "procesos",
        "manual",
        "automatizacion",
        "automation",
        "rag",
        "ai",
        "ia",
    )
    return any(signal in text for signal in signals)


def _has_budget_or_growth_signal(record: LeadRow | SourceCandidate) -> bool:
    text = _combined_context(record)
    signals = (
        "funding",
        "inversion",
        "inversión",
        "ronda",
        "seed",
        "series",
        "yc",
        "accelerator",
        "aceleradora",
        "hiring",
        "contratando",
        "expansion",
        "expansion",
        "revenue",
        "annual revenue",
        "usd",
        "clientes enterprise",
        "enterprise clients",
    )
    if (
        getattr(record, "annual_revenue", None)
        or getattr(record, "total_funding", None)
        or getattr(record, "latest_funding", None)
    ):
        return True
    return any(signal in text for signal in signals)
