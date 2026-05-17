from typing import Protocol

from app.domain.leads import LeadRow
from app.playbook.loader import dump_playbook_data, load_playbook
from app.services.draft_signal import select_signal_claim
from app.services.evidence import evidence_to_json, extract_evidence_items
from app.services.quality import evaluate_message_quality
from app.services.revision_hash import hash_revision_instruction

from .state import LeadState


class DraftLLM(Protocol):
    def extract_manual_context(self, lead: LeadRow) -> str: ...

    def draft_email(
        self,
        *,
        lead: LeadRow,
        message_angle: str,
        evidence_items: list[dict[str, object]],
        selected_signal: str | None,
        nyvex_relevance: str | None,
        why_now_trigger: str | None,
        max_words: int,
    ) -> tuple[str, str]: ...

    def revise_email(
        self,
        *,
        previous_draft: str,
        revision_instruction: str,
        max_words: int,
    ) -> str: ...

    def validate_email_language(
        self,
        *,
        lead: LeadRow,
        subject: str,
        body: str,
        evidence_items: list[dict[str, object]],
        message_angle: str | None,
        max_words: int,
    ) -> dict[str, object]: ...


class DeterministicDraftLLM:
    def extract_manual_context(self, lead: LeadRow) -> str:
        context_parts = [
            lead.manual_context,
            lead.manual_company_context,
            lead.manual_person_context,
            lead.manual_linkedin_notes,
            lead.manual_company_linkedin_text,
            lead.manual_person_linkedin_text,
        ]
        context = " ".join(part for part in context_parts if part)
        return context or "No manual context provided."

    def draft_email(
        self,
        *,
        lead: LeadRow,
        message_angle: str,
        evidence_items: list[dict[str, object]],
        selected_signal: str | None,
        nyvex_relevance: str | None,
        why_now_trigger: str | None,
        max_words: int,
    ) -> tuple[str, str]:
        first_name = (lead.prospect_name or "hola").split()[0]
        signal = selected_signal or select_signal_claim(
            evidence_items,
            company_name=lead.company_name,
        )
        evidence_claim = signal or "trabaja con operaciones B2B donde el conocimiento pesa mucho"
        friction = (
            message_angle
            or (
                "el conocimiento operativo existe, pero no siempre esta disponible "
                "como flujo accionable"
            )
        )
        body = (
            f"Hola {first_name},\n\n"
            f"Vi que {lead.company_name} {evidence_claim}.\n\n"
            "En empresas B2B con ese tipo de operación suele aparecer una fricción: "
            f"{friction}.\n\n"
            "Desde NYVEX trabajé recientemente en un sistema de IA/RAG para una empresa "
            "B2B de HR software, enfocado justamente en convertir conocimiento disperso en flujos "
            "operativos reales.\n\n"
            f"Creo que podría haber 2-3 ideas aplicables a {lead.company_name}.\n\n"
            "¿Tiene sentido que te las comparta brevemente?"
        )
        words = body.split()
        if len(words) > max_words:
            body = " ".join(words[:max_words])
        return f"Hipótesis para {lead.company_name}", body

    def revise_email(
        self,
        *,
        previous_draft: str,
        revision_instruction: str,
        max_words: int,
    ) -> str:
        revised = f"{previous_draft} Ajuste aplicado: {revision_instruction}"
        words = revised.split()
        if len(words) > max_words:
            revised = " ".join(words[:max_words])
        return revised

    def validate_email_language(
        self,
        *,
        lead: LeadRow,
        subject: str,
        body: str,
        evidence_items: list[dict[str, object]],
        message_angle: str | None,
        max_words: int,
    ) -> dict[str, object]:
        return {
            "passes": True,
            "issues": [],
            "reason": "Deterministic local validator skipped semantic language review.",
        }


def validate_input(state: LeadState) -> dict[str, object]:
    try:
        lead = LeadRow.from_mapping(state["lead"])
    except ValueError as exc:
        return {"status": "error", "error_message": str(exc)}
    return {
        "lead_id": lead.lead_id,
        "action": lead.action.value,
        "status": "validated",
    }


def load_playbook_node(state: LeadState) -> dict[str, object]:
    if state.get("status") == "error":
        return {}
    return {"playbook": dump_playbook_data(load_playbook())}


def extract_manual_context_node(llm: DraftLLM) -> callable:
    def node(state: LeadState) -> dict[str, object]:
        if state.get("status") == "error":
            return {}
        lead = LeadRow.from_mapping(state["lead"])
        summary = llm.extract_manual_context(lead)
        evidence_items = evidence_to_json(extract_evidence_items(lead, summary))
        return {
            "manual_context_summary": summary,
            "evidence_items": evidence_items,
            "status": "context_extracted",
        }

    return node


def score_fit(state: LeadState) -> dict[str, object]:
    if state.get("status") == "error":
        return {}
    lead = LeadRow.from_mapping(state["lead"])
    playbook = state["playbook"]
    industries = {industry.lower() for industry in playbook["icp"]["industries"]}
    score = 55
    reasons = ["baseline B2B fit"]

    if lead.industry and lead.industry.lower() in industries:
        score += 25
        reasons.append("industry matches ICP")
    if lead.company_website:
        score += 10
        reasons.append("company website present")
    if state.get("manual_context_summary") != "No manual context provided.":
        score += 10
        reasons.append("manual context available")

    return {
        "fit_score": min(score, 100),
        "fit_score_reason": "; ".join(reasons),
        "status": "scored",
    }


def select_message_angle(state: LeadState) -> dict[str, object]:
    if state.get("status") == "error":
        return {}
    if state.get("draft_friction_hypothesis"):
        return {
            "message_angle": str(state["draft_friction_hypothesis"]),
            "status": "angle_selected",
        }
    playbook = state["playbook"]
    value_prop = playbook["value_props"][0]
    return {
        "message_angle": value_prop["outcome"],
        "status": "angle_selected",
    }


def draft_message_node(llm: DraftLLM) -> callable:
    def node(state: LeadState) -> dict[str, object]:
        if state.get("status") == "error":
            return {}
        lead = LeadRow.from_mapping(state["lead"])
        max_words = int(state["playbook"]["message_rules"]["max_words_email"])
        subject, body = llm.draft_email(
            lead=lead,
            message_angle=state["message_angle"],
            evidence_items=state.get("evidence_items", []),
            selected_signal=state.get("draft_signal_claim"),
            nyvex_relevance=state.get("draft_nyvex_relevance"),
            why_now_trigger=state.get("draft_why_now_trigger"),
            max_words=max_words,
        )
        return {
            "email_subject": subject,
            "email_draft": body,
            "status": "drafted",
        }

    return node


def evaluate_draft(state: LeadState) -> dict[str, object]:
    if state.get("status") == "error":
        return {}
    draft = state.get("revised_draft") or state.get("email_draft", "")
    playbook = state["playbook"]
    quality = evaluate_message_quality(
        message=draft,
        max_words=int(playbook["message_rules"]["max_words_email"]),
        avoid_phrases=playbook["message_rules"]["avoid_phrases"],
        evidence_items=state.get("evidence_items", []),
    )
    return {
        "quality_score": quality.score,
        "quality_issues": quality.issues,
        "status": _status_after_quality(state, quality.score),
    }


def revise_message_node(llm: DraftLLM) -> callable:
    def node(state: LeadState) -> dict[str, object]:
        if state.get("status") == "error":
            return {}
        lead = LeadRow.from_mapping(state["lead"])
        manual_context_summary = llm.extract_manual_context(lead)
        evidence_items = evidence_to_json(extract_evidence_items(lead, manual_context_summary))
        previous_draft = lead.revised_draft or lead.email_draft
        if not previous_draft:
            return {
                "status": "error",
                "error_message": "previous draft is required when action is revise",
            }
        revision_hash = hash_revision_instruction(lead.revision_instruction)
        if revision_hash == lead.last_processed_revision_hash:
            return {
                "status": "revised",
                "revision_instruction_hash": revision_hash,
                "last_processed_revision_hash": lead.last_processed_revision_hash,
                "revision_count": lead.revision_count,
                "revised_draft": previous_draft,
                "manual_context_summary": manual_context_summary,
                "evidence_items": evidence_items,
                "agent_note": "Revision instruction already processed.",
            }
        revised = llm.revise_email(
            previous_draft=previous_draft,
            revision_instruction=lead.revision_instruction or "",
            max_words=int(state["playbook"]["message_rules"]["max_words_email"]),
        )
        return {
            "revised_draft": revised,
            "revision_instruction_hash": revision_hash,
            "last_processed_revision_hash": revision_hash,
            "revision_count": lead.revision_count + 1,
            "manual_context_summary": manual_context_summary,
            "evidence_items": evidence_items,
            "status": "revised",
        }

    return node


def write_revision_result(state: LeadState) -> dict[str, object]:
    if state.get("status") == "error":
        return {"agent_note": "Revision failed."}
    if state.get("agent_note") == "Revision instruction already processed.":
        return {}
    return {
        "agent_note": (
            f"Revision applied. Revision count is {state.get('revision_count')}; "
            f"quality score is {state.get('quality_score')}."
        )
    }


def _status_after_quality(state: LeadState, quality_score: int) -> str:
    if quality_score < 70:
        return "needs_revision"
    if state.get("action") == "revise":
        return "revised"
    return "drafted"


def write_graph_result(state: LeadState) -> dict[str, object]:
    if state.get("status") == "error":
        return {"agent_note": "Graph failed before drafting."}
    return {
        "agent_note": (
            f"Draft generated with fit score {state.get('fit_score')} "
            f"and quality score {state.get('quality_score')}."
        )
    }
