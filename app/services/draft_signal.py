from __future__ import annotations

from dataclasses import dataclass

from app.domain.enrichment import EnrichmentResult, EvidenceItem, EvidenceSourceType

OPERATIONAL_SIGNAL_KEYWORDS = (
    "adopcion de ia",
    "adopciÃ³n de ia",
    "academy",
    "ai adoption",
    "anomal",
    "api",
    "asset performance",
    "automatizacion",
    "automatizaciÃ³n",
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
    "field data",
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
    "on-the-job",
    "operaciones",
    "operations",
    "plataforma",
    "platform",
    "portal",
    "process automation",
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
    "kpi",
    "reportes",
    "reporting",
    "scada",
    "training",
    "entrenamiento",
    "workflow",
)

SUPPORTING_TRIGGER_KEYWORDS = (
    "contratando",
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

TIME_SENSITIVE_KEYWORDS = (
    "hace ",
    "last month",
    "last week",
    "recent",
    "reciente",
    "recently",
    "today",
    "yesterday",
)

HIRING_PRIMARY_KEYWORDS = (
    "career",
    "careers",
    "contratando",
    "hiring",
    "job",
    "jobs",
    "nuevo talento",
    "nuevos talentos",
    "open role",
    "roles",
    "vacante",
    "vacantes",
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
    signal_type: str | None = None
    friction_hypothesis: str | None = None
    why_now_trigger: str | None = None
    nyvex_relevance: str | None = None
    solution_fit_type: str | None = None
    nyvex_positioning: str | None = None
    supporting_evidence_ids: list[str] | None = None
    signal_source_quality: str | None = None
    system_worthiness: str | None = None
    why_not_chatgpt_task: str | None = None
    risk_notes: list[str] | None = None
    message_brief: dict[str, object] | None = None
    reason: str = ""


def assess_draft_signal(result: EnrichmentResult) -> DraftSignalAssessment:
    """Require a concrete, pain-adjacent signal before allowing outbound copy."""
    evidence_items = result.evidence_items or []
    selected_pair = _select_signal_evidence_with_index(evidence_items)
    selected = selected_pair[1] if selected_pair else None
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

    selected_index = selected_pair[0] if selected_pair else 0
    signal_text = _safe_opener_claim(result, selected)
    if not signal_text:
        return DraftSignalAssessment(
            ready=False,
            reason="The available signal is too vague to use in a first email.",
        )

    source_quality = _source_quality(selected)
    careers_without_confirmation = (
        selected.source_type == EvidenceSourceType.CAREERS
        and not _has_confirming_non_careers_evidence(evidence_items, selected)
    )
    if careers_without_confirmation:
        return DraftSignalAssessment(
            ready=False,
            reason=(
                "Careers or hiring evidence can support timing, but it is too weak "
                "as the main opener without separate product, operations, support, "
                "implementation, data, or customer-process evidence."
            ),
        )

    solution_fit_type = _solution_fit_type(result, selected)
    system_worthiness = _system_worthiness(result, selected, solution_fit_type)
    if system_worthiness == "low":
        return DraftSignalAssessment(
            ready=False,
            reason=(
                "The signal points to a one-off AI prompt or simple manual task, "
                "not a system-level NYVEX opportunity."
            ),
        )

    evidence_id = _evidence_id(selected_index)
    friction = _friction_from_result(result, selected)
    nyvex_relevance = _nyvex_relevance_from_signal(result, selected)
    nyvex_positioning = _nyvex_positioning(result, selected)
    why_not_chatgpt_task = _why_not_chatgpt_task(result, selected, solution_fit_type)
    risk_notes = _risk_notes(result, selected, source_quality)
    message_brief = {
        "selected_signal": signal_text,
        "raw_selected_evidence_claim": selected.claim,
        "supporting_evidence_ids": [evidence_id],
        "source_quality": source_quality,
        "can_use_as_opener": True,
        "solution_fit_type": solution_fit_type,
        "system_worthiness": system_worthiness,
        "why_not_chatgpt_task": why_not_chatgpt_task,
        "nyvex_angle": nyvex_relevance,
        "friction_hypothesis": friction,
        "nyvex_positioning": nyvex_positioning,
        "risk_notes": risk_notes,
        "drafting_policy": (
            "Use selected_signal as the opener fact. Do not upgrade it into broader "
            "claims, do not use hiring/funding as the opener, and do not propose "
            "one-off ChatGPT-style tasks."
        ),
    }

    return DraftSignalAssessment(
        ready=True,
        signal_claim=signal_text,
        signal_type=_signal_type(selected),
        friction_hypothesis=friction,
        why_now_trigger=_clean_trigger(trigger.claim, result.company_name)
        if trigger
        else None,
        nyvex_relevance=nyvex_relevance,
        solution_fit_type=solution_fit_type,
        nyvex_positioning=nyvex_positioning,
        supporting_evidence_ids=[evidence_id],
        signal_source_quality=source_quality,
        system_worthiness=system_worthiness,
        why_not_chatgpt_task=why_not_chatgpt_task,
        risk_notes=risk_notes,
        message_brief=message_brief,
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
    selected = _select_signal_evidence_with_index(evidence_items)
    return selected[1] if selected else None


def _select_signal_evidence_with_index(
    evidence_items: list[EvidenceItem],
) -> tuple[int, EvidenceItem] | None:
    scored: list[tuple[int, int, EvidenceItem]] = []
    for index, item in enumerate(evidence_items):
        text = " ".join(
            part for part in (item.claim, item.quote_or_summary or "") if part
        ).lower()
        operational_hits = _keyword_hits(text, OPERATIONAL_SIGNAL_KEYWORDS)
        trigger_hits = _keyword_hits(text, SUPPORTING_TRIGGER_KEYWORDS)
        milestone_hits = _keyword_hits(text, MILESTONE_OR_CREDENTIAL_KEYWORDS)
        decorative_hits = _keyword_hits(text, DECORATIVE_ONLY_KEYWORDS)
        if not operational_hits:
            continue
        if (
            item.source_type == EvidenceSourceType.CAREERS
            and _keyword_hits(text, HIRING_PRIMARY_KEYWORDS)
        ):
            continue
        if _is_hiring_or_role_primary_signal(text):
            continue
        if _is_time_sensitive_primary_signal(text) and not _has_stable_operational_surface(text):
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
            scored.append((score, index, item))
    if not scored:
        return None
    selected = sorted(scored, key=lambda pair: pair[0], reverse=True)[0]
    return selected[1], selected[2]


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
        time_hits = _keyword_hits(text, TIME_SENSITIVE_KEYWORDS)
        hiring_hits = _keyword_hits(text, HIRING_PRIMARY_KEYWORDS)
        if not trigger_hits and not milestone_hits and not time_hits and not hiring_hits:
            continue
        score = (
            (trigger_hits + milestone_hits + time_hits + hiring_hits) * 20
            + min(max(item.confidence, 0), 100) // 10
        )
        scored.append((score, item))
    if not scored:
        return None
    return sorted(scored, key=lambda pair: pair[0], reverse=True)[0][1]


def _friction_from_result(result: EnrichmentResult, signal: EvidenceItem) -> str:
    fit_friction = _fit_specific_friction(result, signal)
    if result.operational_pain_hypothesis:
        return _generalize_friction(result.operational_pain_hypothesis, fit_friction)

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
    return fit_friction


def _generalize_friction(text: str, fallback: str) -> str:
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
        return fallback
    if _looks_like_direct_person_diagnosis(lowered):
        return fallback
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


def _safe_opener_claim(result: EnrichmentResult, signal: EvidenceItem) -> str:
    """Build a conservative Spanish opener claim from one allowed evidence item."""
    text = _combined_context(result, signal)

    if any(marker in text for marker in ("bank", "banco", "cooperativa", "digital banking")):
        if any(marker in text for marker in ("onboarding", "origination", "originacion")):
            return (
                "trabaja con instituciones financieras en canales digitales, "
                "onboarding y atencion a clientes"
            )
        return "trabaja con instituciones financieras en operaciones digitales"
    if any(marker in text for marker in ("conversational ai", "ia conversacional", "whatsapp")):
        return (
            "trabaja con IA conversacional para ventas, soporte y operaciones "
            "con clientes"
        )
    if any(marker in text for marker in ("erp", "pos", "wms", "retail", "replenishment")):
        return (
            "conecta datos operativos para apoyar decisiones de inventario, "
            "abastecimiento y retail"
        )
    if any(marker in text for marker in ("scada", "field data", "asset performance")):
        return (
            "centraliza datos operativos para priorizar acciones en activos "
            "renovables"
        )
    if any(marker in text for marker in ("payment", "pagos", "subscription", "suscrip")):
        return (
            "trabaja con pagos, suscripciones e integraciones operativas para "
            "empresas en LATAM"
        )
    if any(marker in text for marker in ("marketplace", "cross-border", "seller", "ecommerce")):
        return (
            "opera flujos de ecommerce y marketplace cross-border en la region"
        )
    if any(
        marker in text
        for marker in (
            "ai adoption",
            "adopcion de ia",
            "adopciÃƒÂ³n de ia",
            "process automation",
            "training",
            "entrenamiento",
        )
    ):
        return (
            "trabaja en adopcion de IA y automatizacion de procesos para equipos B2B"
        )
    if any(marker in text for marker in ("help center", "knowledge base", "documentation")):
        return "tiene documentacion y conocimiento operativo de cara a clientes"
    if any(marker in text for marker in ("support", "soporte", "ticket")):
        return "tiene una operacion de soporte donde el conocimiento pesa mucho"
    if any(marker in text for marker in ("implementation", "implementacion", "onboarding")):
        return "tiene procesos de implementacion y onboarding para clientes B2B"

    return _sentence_safe_trim(_clean_claim(signal.claim, result.company_name), 130)


def _source_quality(item: EvidenceItem) -> str:
    if item.source_type in {
        EvidenceSourceType.HELP_CENTER,
        EvidenceSourceType.MANUAL_CONTEXT,
        EvidenceSourceType.WEBSITE,
    }:
        return "high" if item.confidence >= 75 else "medium"
    if item.source_type in {EvidenceSourceType.BLOG, EvidenceSourceType.SEARCH_RESULT}:
        return "medium" if item.confidence >= 70 else "low"
    if item.source_type == EvidenceSourceType.CAREERS:
        return "weak_primary_signal"
    return "low"


def _has_confirming_non_careers_evidence(
    evidence_items: list[EvidenceItem],
    selected: EvidenceItem,
) -> bool:
    selected_text = f"{selected.claim} {selected.quote_or_summary or ''}".lower()
    for item in evidence_items:
        if item == selected or item.source_type == EvidenceSourceType.CAREERS:
            continue
        text = f"{item.claim} {item.quote_or_summary or ''}".lower()
        if _has_solution_adjacent_signal(text) and (
            _token_overlap_text(selected_text, text) >= 0.20
            or _keyword_hits(text, OPERATIONAL_SIGNAL_KEYWORDS) >= 2
        ):
            return True
    return False


def _system_worthiness(
    result: EnrichmentResult,
    signal: EvidenceItem,
    solution_fit_type: str,
) -> str:
    text = _combined_context(result, signal)
    architecture_markers = (
        "api",
        "crm",
        "data",
        "datos",
        "erp",
        "field data",
        "help center",
        "integration",
        "integracion",
        "knowledge base",
        "permissions",
        "permisos",
        "reglas",
        "rules",
        "scada",
        "tickets",
        "traceability",
        "trazabilidad",
        "webhook",
        "workflow",
    )
    trivial_markers = (
        "checklist",
        "notas",
        "one-off",
        "resumir",
        "summarize",
        "tomar notas",
    )
    if any(marker in text for marker in trivial_markers) and not any(
        marker in text for marker in architecture_markers
    ):
        return "low"
    if solution_fit_type in {"data_ops_fit", "agentic_workflow_fit", "direct_rag_fit"}:
        return "high"
    if any(marker in text for marker in architecture_markers):
        return "medium"
    return "medium"


def _why_not_chatgpt_task(
    result: EnrichmentResult,
    signal: EvidenceItem,
    solution_fit_type: str,
) -> str:
    if solution_fit_type == "direct_rag_fit":
        return (
            "The angle requires retrieval over company knowledge, permissions, "
            "repeatable answers and operational handoff, not a one-off summary."
        )
    if solution_fit_type == "data_ops_fit":
        return (
            "The angle involves live data, business rules, exceptions and repeatable "
            "decisions across systems."
        )
    if solution_fit_type == "agentic_workflow_fit":
        return (
            "The angle involves routing, actions, tool use, human review and "
            "traceable workflow execution."
        )
    return (
        "The email should explore a tailored system opportunity; avoid pitching "
        "manual prompting, generic chatbots or one-off content generation."
    )


def _risk_notes(
    result: EnrichmentResult,
    signal: EvidenceItem,
    source_quality: str,
) -> list[str]:
    notes: list[str] = []
    text = _combined_context(result, signal)
    if signal.source_type == EvidenceSourceType.CAREERS:
        notes.append("Careers evidence is timing context only; do not use hiring as opener.")
    if source_quality in {"low", "weak_primary_signal"}:
        notes.append("Use a cautious opener because the selected source is not strong.")
    if _is_time_sensitive_primary_signal(text):
        notes.append("Avoid exact recency unless the date is explicit and still relevant.")
    if _is_adjacent_ai_vendor(text):
        notes.append("Prospect may already sell AI; position NYVEX as exploratory/custom.")
    return notes


def _evidence_id(index: int) -> str:
    return f"ev_{index + 1}"


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


def _solution_fit_type(result: EnrichmentResult, signal: EvidenceItem) -> str:
    text = _combined_context(result, signal)
    if _is_adjacent_ai_vendor(text):
        return "exploratory_custom_solution"
    if any(
        keyword in text
        for keyword in (
            "anomal",
            "asset performance",
            "conciliaci",
            "data",
            "datos",
            "erp",
            "field data",
            "kpi",
            "logistica",
            "logistics",
            "pagos",
            "payment",
            "pos",
            "reconciliation",
            "reporting",
            "scada",
            "supply chain",
            "wms",
        )
    ):
        return "data_ops_fit"
    if any(
        keyword in text
        for keyword in (
            "base de conocimiento",
            "documentation",
            "documentacion",
            "documentaci",
            "help center",
            "knowledge base",
            "runbook",
            "soporte",
            "support",
            "ticket",
        )
    ):
        return "direct_rag_fit"
    if any(
        keyword in text
        for keyword in (
            "agent",
            "agente",
            "automatizaci",
            "automation",
            "crm",
            "customer success",
            "implementation",
            "implementaci",
            "onboarding",
            "workflow",
        )
    ):
        return "agentic_workflow_fit"
    return "exploratory_custom_solution"


def _nyvex_positioning(result: EnrichmentResult, signal: EvidenceItem) -> str:
    fit = _solution_fit_type(result, signal)
    if fit == "direct_rag_fit":
        return (
            "Desde NYVEX trabajé recientemente en un sistema de IA/RAG para una "
            "empresa B2B de software de RRHH, enfocado en convertir conocimiento "
            "disperso en flujos operativos reales."
        )
    if fit == "data_ops_fit":
        return (
            "Desde NYVEX vengo trabajando en sistemas de IA aplicados a procesos "
            "reales, incluyendo IA/RAG y agentes cuando ayudan a ordenar datos, "
            "criterios y flujos operativos."
        )
    if fit == "agentic_workflow_fit":
        return (
            "Desde NYVEX vengo trabajando en sistemas de IA aplicados a procesos "
            "reales, incluyendo agentes y RAG cuando sirven para convertir criterio "
            "operativo en flujos reutilizables."
        )
    return (
        "Desde NYVEX vengo trabajando en sistemas de IA aplicados a procesos reales; "
        "mi interés sería explorar hipótesis concretas, no vender una solución genérica."
    )


def _signal_type(item: EvidenceItem) -> str:
    text = " ".join(part for part in (item.claim, item.quote_or_summary or "") if part).lower()
    if _is_time_sensitive_primary_signal(text):
        return "time_sensitive_operational_signal"
    return "durable_operational_signal"


def _fit_specific_friction(result: EnrichmentResult, signal: EvidenceItem) -> str:
    fit = _solution_fit_type(result, signal)
    if fit == "direct_rag_fit":
        return (
            "el conocimiento existe, pero queda repartido entre documentaciÃ³n, "
            "tickets, onboarding y personas clave"
        )
    if fit == "data_ops_fit":
        return (
            "convertir datos, reglas y excepciones operativas en decisiones "
            "repetibles suele depender demasiado de coordinaciÃ³n manual"
        )
    if fit == "agentic_workflow_fit":
        return (
            "los handoffs entre equipos, herramientas y clientes dependen de criterio "
            "manual que deberÃ­a convertirse en acciones repetibles"
        )
    return (
        "cuando la empresa ya trabaja con IA o software avanzado, el valor suele estar "
        "en ordenar workflows internos, datos y decisiones con trazabilidad"
    )


def _has_solution_adjacent_signal(text: str) -> bool:
    solution_keywords = (
        "adopcion de ia",
        "adopciÃ³n de ia",
        "academy",
        "ai adoption",
        "anomal",
        "api",
        "asset performance",
        "automatizaci",
        "base de conocimiento",
        "centro de ayuda",
        "crm",
        "customer success",
        "customer engagement",
        "documentation",
        "documentacion",
        "documentaciÃ³n",
        "erp",
        "field data",
        "help center",
        "implementacion",
        "implementaciÃ³n",
        "implementation",
        "integration",
        "integracion",
        "integraciÃ³n",
        "knowledge base",
        "onboarding",
        "on-the-job",
        "process automation",
        "reporting",
        "scada",
        "runbook",
        "soporte",
        "support",
        "ticket",
        "whatsapp",
        "workflow",
        "training",
        "entrenamiento",
    )
    return any(keyword in text for keyword in solution_keywords)


def _has_stable_operational_surface(text: str) -> bool:
    stable_markers = (
        "adopcion",
        "anomal",
        "api",
        "automatizaci",
        "crm",
        "documentaci",
        "documentation",
        "erp",
        "field data",
        "help center",
        "implementation",
        "implementacion",
        "logistica",
        "logistics",
        "marketplace",
        "onboarding",
        "pagos",
        "payments",
        "platform",
        "plataforma",
        "product",
        "producto",
        "solution",
        "soluci",
        "soporte",
        "support",
        "workflow",
        "scada",
        "training",
        "entrenamiento",
    )
    return any(marker in text for marker in stable_markers)


def _is_hiring_or_role_primary_signal(text: str) -> bool:
    if not _keyword_hits(text, HIRING_PRIMARY_KEYWORDS):
        return False
    hard_hiring_markers = (
        "career",
        "careers",
        "contratando",
        "hiring",
        "jobs",
        "open role",
        "roles",
        "vacante",
        "vacantes",
    )
    if "on-the-job" in text and not any(marker in text for marker in hard_hiring_markers):
        return False
    role_context = (
        "career",
        "careers",
        "engineer",
        "head of",
        "job",
        "jobs",
        "manager",
        "role",
        "roles",
        "specialist",
        "talento",
        "talentos",
        "vacante",
        "vacantes",
    )
    product_context = (
        "ayuda",
        "helps",
        "ofrece",
        "offers",
        "platform",
        "plataforma",
        "product",
        "producto",
        "serves",
        "solution",
        "soluci",
        "trabaja con",
        "works with",
    )
    return any(marker in text for marker in role_context) and not any(
        marker in text for marker in product_context
    )


def _is_time_sensitive_primary_signal(text: str) -> bool:
    primary_markers = (
        "announced",
        "anunci",
        "event",
        "evento",
        "funding",
        "hiring",
        "lanz",
        "launched",
        "levant",
        "raised",
        "reciente",
        "recently",
        "series ",
        "summit",
    )
    return any(marker in text for marker in primary_markers)


def _is_adjacent_ai_vendor(text: str) -> bool:
    markers = (
        "adopcion de ia",
        "adopciÃ³n de ia",
        "agentes de ia",
        "ai adoption",
        "ai agents",
        "ai training",
        "ai at the core",
        "ai is their core",
        "already builds ai",
        "already sells ai",
        "conversational ai",
        "ia conversacional",
        "plataforma de ai",
        "plataforma de ia",
        "sells ai",
        "entrenamiento en ia",
        "vende adopcion de ia",
    )
    return any(marker in text for marker in markers)


def _combined_context(result: EnrichmentResult, signal: EvidenceItem) -> str:
    parts = [
        signal.claim,
        signal.quote_or_summary or "",
        result.company_summary or "",
        result.operational_pain_hypothesis or "",
        result.possible_ai_use_case or "",
        result.personalization_angle or "",
        " ".join(result.risk_flags or []),
    ]
    return " ".join(part for part in parts if part).lower()


def _keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _token_overlap_text(left: str, right: str) -> float:
    left_tokens = {
        token
        for token in left.replace("/", " ").replace("-", " ").split()
        if len(token) > 3
    }
    right_tokens = {
        token
        for token in right.replace("/", " ").replace("-", " ").split()
        if len(token) > 3
    }
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))


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
