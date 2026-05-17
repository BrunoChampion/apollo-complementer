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
    "customer engagement",
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
    "sales funnels",
    "whatsapp",
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

MILESTONE_OR_CREDENTIAL_KEYWORDS = (
    "certification",
    "certificacion",
    "certificaciÃ³n",
    "compliance report",
    "cumplimiento",
    "informe",
    "iso ",
    "soc 2",
    "soc 3",
    "type ii",
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
    why_now_trigger: str | None = None
    nyvex_relevance: str | None = None
    reason: str = ""


def assess_draft_signal(result: EnrichmentResult) -> DraftSignalAssessment:
    """Require a concrete, pain-adjacent signal before allowing outbound copy."""
    evidence_items = result.evidence_items or []
    selected = _select_signal_evidence(evidence_items)
    trigger = _select_why_now_trigger(evidence_items, selected)
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
        why_now_trigger=_clean_trigger(trigger.claim, result.company_name)
        if trigger
        else None,
        nyvex_relevance=_nyvex_relevance_from_signal(result, selected),
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
        operational_hits = _keyword_hits(text, OPERATIONAL_SIGNAL_KEYWORDS)
        trigger_hits = _keyword_hits(text, SUPPORTING_TRIGGER_KEYWORDS)
        milestone_hits = _keyword_hits(text, MILESTONE_OR_CREDENTIAL_KEYWORDS)
        decorative_hits = _keyword_hits(text, DECORATIVE_ONLY_KEYWORDS)
        if not operational_hits:
            continue
        if trigger_hits and not _has_solution_adjacent_signal(text):
            continue
        if milestone_hits and not _has_solution_adjacent_signal(text):
            continue

        score = 0
        if item.source_type in {
            EvidenceSourceType.HELP_CENTER,
            EvidenceSourceType.MANUAL_CONTEXT,
        }:
            score += 20
        if item.source_type == EvidenceSourceType.CAREERS:
            score -= 25
        score += min(60, operational_hits * 15)
        if _has_solution_adjacent_signal(text):
            score += 30
        if trigger_hits:
            score -= min(35, trigger_hits * 12)
        if milestone_hits:
            score -= min(45, milestone_hits * 15)
        if decorative_hits:
            score -= 10
        score += min(max(item.confidence, 0), 100) // 10
        if score >= 45:
            scored.append((score, item))
    if not scored:
        return None
    return sorted(scored, key=lambda pair: pair[0], reverse=True)[0][1]


def _select_why_now_trigger(
    evidence_items: list[EvidenceItem],
    selected_signal: EvidenceItem | None,
) -> EvidenceItem | None:
    scored: list[tuple[int, EvidenceItem]] = []
    for item in evidence_items:
        if selected_signal is not None and item == selected_signal:
            continue
        text = " ".join(
            part for part in (item.claim, item.quote_or_summary or "") if part
        ).lower()
        trigger_hits = _keyword_hits(text, SUPPORTING_TRIGGER_KEYWORDS)
        milestone_hits = _keyword_hits(text, MILESTONE_OR_CREDENTIAL_KEYWORDS)
        if not trigger_hits and not milestone_hits:
            continue
        score = (trigger_hits + milestone_hits) * 20 + min(max(item.confidence, 0), 100) // 10
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
    if _looks_like_direct_person_diagnosis(lowered):
        return (
            "el conocimiento operativo existe, pero no siempre esta disponible como "
            "flujo accionable para soporte, onboarding, implementacion o customer success"
        )
    return _sentence_safe_trim(cleaned, 180)


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


def _clean_trigger(claim: str, company_name: str | None) -> str:
    return _sentence_safe_trim(_clean_claim(claim, company_name), 160)


def _nyvex_relevance_from_signal(
    result: EnrichmentResult,
    signal: EvidenceItem,
) -> str:
    if result.possible_ai_use_case:
        return _sentence_safe_trim(result.possible_ai_use_case.strip(), 220)
    text = f"{signal.claim} {signal.quote_or_summary or ''}".lower()
    if any(keyword in text for keyword in ("support", "soporte", "help center", "ticket")):
        return "explorar un copilot/RAG para soporte, tickets y documentacion operativa"
    if any(keyword in text for keyword in ("onboarding", "implement")):
        return "explorar flujos de IA para onboarding, implementacion y handoffs"
    if any(keyword in text for keyword in ("api", "integration", "integrac", "erp", "crm")):
        return "explorar automatizacion de integraciones, datos y documentacion tecnica"
    return "explorar hipotesis de IA/RAG/agentes sobre conocimiento operativo disperso"


def _has_solution_adjacent_signal(text: str) -> bool:
    solution_keywords = (
        "academy",
        "api",
        "base de conocimiento",
        "centro de ayuda",
        "crm",
        "customer success",
        "customer engagement",
        "documentation",
        "documentacion",
        "documentaciÃ³n",
        "erp",
        "help center",
        "implementacion",
        "implementaciÃ³n",
        "implementation",
        "integration",
        "integracion",
        "integraciÃ³n",
        "knowledge base",
        "onboarding",
        "runbook",
        "soporte",
        "support",
        "ticket",
        "whatsapp",
        "workflow",
    )
    return any(keyword in text for keyword in solution_keywords)


def _keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _looks_like_direct_person_diagnosis(text: str) -> bool:
    markers = (
        "as coo",
        "as founder",
        "owns ",
        "is likely",
        "appears to",
        "responsible for",
        "near-term priority",
    )
    return any(marker in text for marker in markers)


def _sentence_safe_trim(text: str, max_chars: int) -> str:
    cleaned = " ".join(text.strip().split())
    if len(cleaned) <= max_chars:
        return cleaned.rstrip(".")
    window = cleaned[:max_chars].rstrip()
    for separator in (". ", "; ", ", "):
        index = window.rfind(separator)
        if index >= 60:
            return window[:index].strip().rstrip(".")
    return window.rsplit(" ", 1)[0].strip().rstrip(".")


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
