import logging

from app.domain.enrichment import EnrichmentResult, RecommendedAction
from app.graph.state import LeadState
from app.services.draft_signal import assess_draft_signal

logger = logging.getLogger(__name__)


def gate_draft_on_enrichment(state: LeadState) -> dict[str, object]:
    """Gate: only proceed to draft if enrichment recommends draft."""
    if state.get("status") == "error":
        return {}
    lead = state.get("lead", {})
    lead_id = state.get("lead_id") or lead.get("lead_id")
    enrichment_dict = state.get("enrichment_result", {})
    try:
        result = EnrichmentResult.model_validate(enrichment_dict)
    except Exception:
        logger.info(
            "draft.gate.error run_id=%s lead_id=%s reason=invalid_enrichment_result",
            state.get("run_id"),
            lead_id,
        )
        return {
            "status": "error",
            "error_message": "Invalid enrichment result in state.",
        }

    if result.enrichment_status.value == "insufficient_data":
        logger.info(
            "draft.gate.blocked run_id=%s lead_id=%s reason=insufficient_data",
            state.get("run_id"),
            lead_id,
        )
        return {
            "status": "insufficient_data",
            "agent_note": (
                f"Insufficient data for {result.company_name or 'company'}. "
                "No draft generated."
            ),
        }

    if result.recommended_action != RecommendedAction.DRAFT:
        logger.info(
            "draft.gate.blocked run_id=%s lead_id=%s reason=recommended_action action=%s",
            state.get("run_id"),
            lead_id,
            result.recommended_action.value,
        )
        return {
            "status": "needs_manual_research",
            "agent_note": (
                f"Enrichment recommended {result.recommended_action.value} "
                f"for {result.company_name or 'company'}. No draft generated."
            ),
        }

    if result.confidence_score is not None and result.confidence_score < 65:
        logger.info(
            "draft.gate.blocked run_id=%s lead_id=%s reason=low_confidence confidence=%s",
            state.get("run_id"),
            lead_id,
            result.confidence_score,
        )
        return {
            "status": "needs_manual_research",
            "agent_note": (
                f"Confidence too low ({result.confidence_score}) for "
                f"{result.company_name or 'company'}. No draft generated."
            ),
        }

    if not result.evidence_items or len(result.evidence_items) == 0:
        logger.info(
            "draft.gate.blocked run_id=%s lead_id=%s reason=no_evidence",
            state.get("run_id"),
            lead_id,
        )
        return {
            "status": "needs_manual_research",
            "agent_note": (
                f"No evidence items for {result.company_name or 'company'}. "
                "No draft generated."
            ),
        }

    signal = assess_draft_signal(result)
    if not signal.ready:
        logger.info(
            "draft.gate.blocked run_id=%s lead_id=%s reason=no_operational_signal",
            state.get("run_id"),
            lead_id,
        )
        return {
            "status": "needs_manual_research",
            "agent_note": f"Draft blocked: {signal.reason}",
        }

    logger.info(
        "draft.gate.passed run_id=%s lead_id=%s confidence=%s evidence_count=%s",
        state.get("run_id"),
        lead_id,
        result.confidence_score,
        len(result.evidence_items or []),
    )
    return {
        "status": "gated_ok",
        "draft_signal_claim": signal.signal_claim,
        "draft_signal_type": signal.signal_type,
        "draft_friction_hypothesis": signal.friction_hypothesis,
        "draft_signal_reason": signal.reason,
        "draft_why_now_trigger": signal.why_now_trigger,
        "draft_nyvex_relevance": signal.nyvex_relevance,
        "draft_solution_fit_type": signal.solution_fit_type,
        "draft_nyvex_positioning": signal.nyvex_positioning,
    }


def write_enrich_and_draft_result(state: LeadState) -> dict[str, object]:
    if state.get("status") == "error":
        logger.info(
            "draft.write_result.error run_id=%s lead_id=%s",
            state.get("run_id"),
            state.get("lead_id") or state.get("lead", {}).get("lead_id"),
        )
        return {"agent_note": "Enrich and draft failed."}
    if state.get("status") == "insufficient_data":
        logger.info(
            "draft.write_result.no_draft run_id=%s lead_id=%s status=insufficient_data",
            state.get("run_id"),
            state.get("lead_id") or state.get("lead", {}).get("lead_id"),
        )
        return {"agent_note": state.get("agent_note", "Insufficient data. No draft generated.")}
    if state.get("status") == "needs_manual_research":
        logger.info(
            "draft.write_result.no_draft run_id=%s lead_id=%s status=needs_manual_research",
            state.get("run_id"),
            state.get("lead_id") or state.get("lead", {}).get("lead_id"),
        )
        return {"agent_note": state.get("agent_note", "Needs manual research. No draft generated.")}
    if state.get("status") == "needs_revision":
        logger.info(
            "draft.write_result.needs_revision run_id=%s lead_id=%s quality_score=%s",
            state.get("run_id"),
            state.get("lead_id") or state.get("lead", {}).get("lead_id"),
            state.get("quality_score"),
        )
        repair_count = int(state.get("draft_repair_count") or 0)
        if repair_count:
            return {
                "agent_note": (
                    state.get("agent_note", "Draft needs revision.")
                    + f" Auto-repair attempts: {repair_count}."
                )
            }
        return {"agent_note": state.get("agent_note", "Draft needs revision.")}
    logger.info(
        "draft.write_result.done run_id=%s lead_id=%s fit_score=%s quality_score=%s",
        state.get("run_id"),
        state.get("lead_id") or state.get("lead", {}).get("lead_id"),
        state.get("fit_score"),
        state.get("quality_score"),
    )
    return {
        "agent_note": (
            f"Draft generated with fit score {state.get('fit_score')} "
            f"and quality score {state.get('quality_score')}."
        )
    }


def inject_enrichment_context(state: LeadState) -> dict[str, object]:
    """Inject enrichment result as manual context and evidence for drafting."""
    if state.get("status") in {"error", "insufficient_data", "needs_manual_research"}:
        return {}
    enrichment_dict = state.get("enrichment_result", {})
    try:
        result = EnrichmentResult.model_validate(enrichment_dict)
    except Exception:
        return {}

    context_parts = []
    if result.company_summary:
        context_parts.append(f"Company: {result.company_summary}")
    if result.operational_pain_hypothesis:
        context_parts.append(f"Pain: {result.operational_pain_hypothesis}")
    if result.possible_ai_use_case:
        context_parts.append(f"AI Use Case: {result.possible_ai_use_case}")
    if result.personalization_angle:
        context_parts.append(f"Angle: {result.personalization_angle}")
    if result.trigger_summary:
        context_parts.append(f"Trigger: {result.trigger_summary}")
    if state.get("draft_signal_claim"):
        context_parts.append(f"Email Signal: {state.get('draft_signal_claim')}")
    if state.get("draft_friction_hypothesis"):
        context_parts.append(f"Email Friction: {state.get('draft_friction_hypothesis')}")
    if state.get("draft_nyvex_relevance"):
        context_parts.append(f"NYVEX Relevance: {state.get('draft_nyvex_relevance')}")
    if state.get("draft_solution_fit_type"):
        context_parts.append(f"Solution Fit Type: {state.get('draft_solution_fit_type')}")
    if state.get("draft_nyvex_positioning"):
        context_parts.append(f"NYVEX Positioning Line: {state.get('draft_nyvex_positioning')}")
    if state.get("draft_why_now_trigger"):
        context_parts.append(
            "Why Now Trigger (optional context only, not the main opener): "
            f"{state.get('draft_why_now_trigger')}"
        )
    context_parts.append(
        "Drafting Rule: open with the operational signal, not a hiring/funding/expansion "
        "trigger. The signal must make 'ese tipo de operacion' clear. Frame the pain "
        "as a general B2B friction rather than diagnosing the company. Use the NYVEX "
        "positioning line as flexible credibility: the previous RAG project is proof of "
        "technical judgment, not necessarily the exact solution for this prospect. Close "
        "by asking permission to share 2-3 hypotheses."
    )

    summary = "\n".join(context_parts) or "No enrichment context available."

    evidence_json = []
    for item in result.evidence_items or []:
        evidence_json.append({
            "claim": item.claim,
            "source_type": item.source_type.value,
            "source_url": item.source_url,
            "quote_or_summary": item.quote_or_summary,
            "confidence": item.confidence,
            "used_in_message": item.used_in_message,
        })

    logger.info(
        "draft.inject_context.done run_id=%s lead_id=%s evidence_count=%s",
        state.get("run_id"),
        state.get("lead_id") or state.get("lead", {}).get("lead_id"),
        len(evidence_json),
    )
    return {
        "manual_context_summary": summary,
        "evidence_items": evidence_json,
        "status": "context_injected",
    }
