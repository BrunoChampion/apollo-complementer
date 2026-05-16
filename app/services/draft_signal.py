from __future__ import annotations

from dataclasses import dataclass

from app.domain.enrichment import EnrichmentResult, EvidenceItem, EvidenceSourceType


OPERATIONAL_SIGNAL_KEYWORDS = (
    "academy",
    "api",
    "base de conocimiento",
    "b2b",
    "centro de ayuda",
    "cliente",
    "clientes",
    "crm",
    "customer success",
    "documentation",
    "documentacion",
    "documentación",
    "enterprise",
    "erp",
    "help center",
    "hubspot",
    "implementacion",
    "implementación",
    "implementation",
    "integration",
    "integracion",
    "integración",
    "knowledge base",
    "marketplace",
    "onboarding",
    "operaciones",
    "operations",
    "plataforma",
    "platform",
    "portal",
    "procesos",
    "retailers",
    "self-service",
    "salesforce",
    "soporte",
    "support",
    "intercom",
    "zendesk",
    "workflow",
)

SUPPORTING_TRIGGER_KEYWORDS = (
    "expansion",
    "expansión",
    "funding",
    "hiring",
    "inversion",
    "inversión",
    "levantó",
    "raised",
    "series",
)

DECORATIVE_ONLY_KEYWORDS = (
    "location",
    "office",
    "oficina",
    "pais",
    "país",
    "website",
)


@dataclass(frozen=True)
class DraftSignalAssessment:
    ready: bool
    signal_claim: str | None = None
    friction_hypothesis: str | None = None
    reason: str = ""


def assess_draft_signal(result: EnrichmentResult) -> DraftSignalAssessment:
    """Require a concrete, pain-adjacent signal before allowing outbound copy."""
    evidence_items = result.evidence_items or []
    selected = _select_signal_evidence(evidence_items)
    if not selected:
        return DraftSignalAssessment(
            ready=False,
            reason=(
                "No concrete operational signal was found for drafting. "
                "Add evidence tied to support, onboarding, implementation, "
                "documentation, integrations, or another real operational friction."
            ),
        )

    signal_text = _clean_claim(selected.claim, result.company_name)
    if not signal_text:
        return DraftSignalAssessment(
            ready=False,
            reason="The available signal is too vague to use in a first email.",
        )

    return DraftSignalAssessment(
        ready=True,
        signal_claim=signal_text,
        friction_hypothesis=_friction_from_result(result, selected),
        reason="Concrete operational signal found for draft.",
    )


def select_signal_claim(
    evidence_items: list[dict[str, object]],
    *,
    company_name: str | None = None,
) -> str | None:
    parsed = []
    for item in evidence_items:
        claim = str(item.get("claim") or "").strip()
        if not claim:
            continue
        parsed.append(
            EvidenceItem(
                claim=claim,
                source_type=item.get("source_type") or EvidenceSourceType.UNKNOWN,
                source_url=item.get("source_url") or None,
                quote_or_summary=item.get("quote_or_summary") or None,
                confidence=_coerce_confidence(item.get("confidence")),
            )
        )
    selected = _select_signal_evidence(parsed)
    if not selected:
        return None
    return _clean_claim(selected.claim, company_name)


def _select_signal_evidence(evidence_items: list[EvidenceItem]) -> EvidenceItem | None:
    scored: list[tuple[int, EvidenceItem]] = []
    for item in evidence_items:
        text = " ".join(
            part for part in (item.claim, item.quote_or_summary or "") if part
        ).lower()
        score = 0
        if item.source_type in {
            EvidenceSourceType.HELP_CENTER,
            EvidenceSourceType.CAREERS,
            EvidenceSourceType.MANUAL_CONTEXT,
        }:
            score += 20
        if any(keyword in text for keyword in OPERATIONAL_SIGNAL_KEYWORDS):
            score += 50
        if any(keyword in text for keyword in SUPPORTING_TRIGGER_KEYWORDS):
            score += 10
        if any(keyword in text for keyword in DECORATIVE_ONLY_KEYWORDS):
            score -= 10
        score += min(max(item.confidence, 0), 100) // 10
        if score >= 45:
            scored.append((score, item))
    if not scored:
        return None
    return sorted(scored, key=lambda pair: pair[0], reverse=True)[0][1]


def _friction_from_result(result: EnrichmentResult, signal: EvidenceItem) -> str:
    if result.operational_pain_hypothesis:
        return _generalize_friction(result.operational_pain_hypothesis)

    signal_text = f"{signal.claim} {signal.quote_or_summary or ''}".lower()
    if any(
        keyword in signal_text
        for keyword in ("help center", "support", "soporte", "documentation", "document")
    ):
        return (
            "el conocimiento existe, pero queda repartido entre documentación, "
            "soporte, onboarding y personas clave"
        )
    if any(keyword in signal_text for keyword in ("api", "integration", "integrac")):
        return (
            "las integraciones y procesos técnicos dependen demasiado de coordinación "
            "manual entre equipos"
        )
    if any(keyword in signal_text for keyword in ("onboarding", "implement")):
        return (
            "la implementación y el onboarding requieren mucho criterio operativo "
            "que no siempre está disponible en el momento correcto"
        )
    return (
        "el conocimiento operativo existe, pero no siempre está disponible como flujo "
        "accionable para el equipo"
    )


def _generalize_friction(text: str) -> str:
    cleaned = text.strip().rstrip(".")
    lowered = cleaned.lower()
    direct_markers = (
        "podria",
        "podría",
        "probablemente",
        "parece que",
        "seguramente",
    )
    if lowered.startswith(direct_markers):
        return (
            "el conocimiento operativo existe, pero no siempre está disponible como "
            "flujo accionable para el equipo"
        )
    return cleaned[:220]


def _clean_claim(claim: str, company_name: str | None) -> str:
    cleaned = " ".join(claim.strip().rstrip(".").split())
    if company_name and cleaned.lower().startswith(company_name.lower()):
        cleaned = cleaned[len(company_name) :].strip(" -:,")

    replacements = (
        ("has an ", "tiene un "),
        ("has a ", "tiene un "),
        ("uses ", "usa "),
        ("sells ", "vende "),
        ("offers ", "ofrece "),
        ("has ", "tiene "),
        ("works with ", "trabaja con "),
    )
    lower = cleaned.lower()
    for source, target in replacements:
        if lower.startswith(source):
            cleaned = target + cleaned[len(source) :]
            break

    return cleaned


def _coerce_confidence(value: object) -> int:
    if isinstance(value, int):
        return min(max(value, 0), 100)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "high":
            return 85
        if normalized == "medium":
            return 65
        if normalized == "low":
            return 40
        try:
            return min(max(int(normalized), 0), 100)
        except ValueError:
            return 50
    return 50
