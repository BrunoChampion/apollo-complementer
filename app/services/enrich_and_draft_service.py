from __future__ import annotations

import json
import logging
from typing import Any

from app.core.markets import country_market_status
from app.domain.enrichment import EnrichmentResult
from app.domain.leads import LeadRow
from app.graph.enrich_and_draft_builder import build_enrich_and_draft_graph
from app.graph.enrichment_builder import build_enrichment_graph
from app.graph.revise_builder import build_revise_enriched_draft_graph
from app.graph.state import LeadState
from app.services.enrichment_review import APPROVE_EXCEPTION, apply_review_decision
from app.services.readiness import validate_readiness

logger = logging.getLogger(__name__)


class EnrichAndDraftService:
    """Orchestrate enrichment + draft with gating based on enrichment quality."""

    def __init__(self) -> None:
        self.enrichment_graph = build_enrichment_graph()
        self.draft_graph = build_enrich_and_draft_graph()
        self.revise_graph = build_revise_enriched_draft_graph()

    def enrich_and_draft(
        self,
        lead: LeadRow,
        run_id: str,
    ) -> dict[str, Any]:
        logger.info(
            "enrich_and_draft.service.start run_id=%s lead_id=%s company=%s",
            run_id,
            lead.lead_id,
            lead.company_name,
        )
        if country_market_status(lead.country) == "unsupported":
            logger.info(
                "enrich_and_draft.service.unsupported_country run_id=%s lead_id=%s country=%s",
                run_id,
                lead.lead_id,
                lead.country,
            )
            return {
                "lead_id": lead.lead_id,
                "status": "discard",
                "agent_note": "Lead country is unsupported for this Spanish-speaking ICP.",
            }

        readiness = validate_readiness(lead)
        if not readiness.ready_for_enrichment:
            status = (
                "discarded"
                if readiness.icp_status == "disqualified"
                else "needs_manual_research"
            )
            return {
                "lead_id": lead.lead_id,
                "status": status,
                "agent_note": (
                    "Enrich-and-draft blocked before web research. "
                    f"{readiness.identity_validation_status}: "
                    f"{readiness.identity_validation_reason}; "
                    f"{readiness.icp_status}: {readiness.icp_score_reason}"
                ),
                **readiness.as_update(),
            }

        # Step 1: Enrichment
        enrichment_state = {
            "run_id": run_id,
            "lead_id": lead.lead_id,
            "lead": lead.model_dump(mode="json"),
        }
        enrichment_output = self.enrichment_graph.invoke(
            enrichment_state,
            config={"configurable": {"thread_id": f"enrich-{lead.lead_id}"}},
        )

        enrichment_dict = enrichment_output.get("enrichment_result", {})
        if not enrichment_dict:
            logger.info(
                "enrich_and_draft.service.no_enrichment_result run_id=%s lead_id=%s",
                run_id,
                lead.lead_id,
            )
            return {
                "lead_id": lead.lead_id,
                "status": "error",
                "agent_note": "Enrichment produced no result.",
            }

        try:
            enrichment_result = EnrichmentResult.model_validate(enrichment_dict)
        except Exception as exc:
            logger.info(
                "enrich_and_draft.service.invalid_enrichment run_id=%s lead_id=%s error=%s",
                run_id,
                lead.lead_id,
                exc,
            )
            return {
                "lead_id": lead.lead_id,
                "status": "error",
                "agent_note": f"Invalid enrichment result: {exc}",
            }
        enrichment_result.user_decision = lead.user_decision
        enrichment_result.user_decision_notes = lead.user_decision_notes
        enrichment_result = apply_review_decision(enrichment_result)
        enrichment_dict = enrichment_result.model_dump(mode="json")

        if (
            enrichment_result.review_required
            and enrichment_result.user_decision != APPROVE_EXCEPTION
        ):
            return {
                "lead_id": lead.lead_id,
                "status": "needs_manual_research",
                "agent_note": (
                    "Draft blocked: review required. "
                    f"{enrichment_result.review_summary or ''}"
                ).strip(),
                "enrichment_result": enrichment_dict,
                "review_required": enrichment_result.review_required,
                "review_category": enrichment_result.review_category,
                "review_summary": enrichment_result.review_summary,
                "review_evidence": enrichment_result.review_evidence,
                "suggested_action": enrichment_result.suggested_action,
                "suggested_action_reason": enrichment_result.suggested_action_reason,
                "ready_for_draft": False,
            }

        # Step 2: Gate on enrichment
        if enrichment_result.recommended_action.value != "draft":
            lead_status = (
                "discarded"
                if enrichment_result.recommended_action.value == "discard"
                else enrichment_result.recommended_action.value
            )
            logger.info(
                "enrich_and_draft.service.gate_no_draft "
                "run_id=%s lead_id=%s action=%s confidence=%s",
                run_id,
                lead.lead_id,
                enrichment_result.recommended_action.value,
                enrichment_result.confidence_score,
            )
            return {
                "lead_id": lead.lead_id,
                "status": lead_status,
                "agent_note": (
                    f"Enrichment recommended {enrichment_result.recommended_action.value}. "
                    f"No draft generated."
                ),
                "enrichment_result": enrichment_dict,
            }

        if (
            enrichment_result.confidence_score is not None
            and enrichment_result.confidence_score < 65
        ):
            logger.info(
                "enrich_and_draft.service.gate_low_confidence run_id=%s lead_id=%s confidence=%s",
                run_id,
                lead.lead_id,
                enrichment_result.confidence_score,
            )
            return {
                "lead_id": lead.lead_id,
                "status": "needs_manual_research",
                "agent_note": (
                    f"Confidence too low ({enrichment_result.confidence_score}). "
                    "No draft generated."
                ),
                "enrichment_result": enrichment_dict,
            }

        if not enrichment_result.evidence_items:
            logger.info(
                "enrich_and_draft.service.gate_no_evidence run_id=%s lead_id=%s",
                run_id,
                lead.lead_id,
            )
            return {
                "lead_id": lead.lead_id,
                "status": "needs_manual_research",
                "agent_note": "No evidence items. No draft generated.",
                "enrichment_result": enrichment_dict,
            }

        # Step 3: Draft with enrichment context
        draft_state: LeadState = {
            "run_id": run_id,
            "lead_id": lead.lead_id,
            "action": "enrich_and_draft",
            "lead": lead.model_dump(mode="json"),
            "enrichment_result": enrichment_dict,
        }
        draft_output = self.draft_graph.invoke(
            draft_state,
            config={"configurable": {"thread_id": f"draft-{lead.lead_id}"}},
        )
        logger.info(
            "enrich_and_draft.service.draft_done run_id=%s lead_id=%s status=%s quality_score=%s",
            run_id,
            lead.lead_id,
            draft_output.get("status", "unknown"),
            draft_output.get("quality_score"),
        )

        return {
            "lead_id": lead.lead_id,
            "status": draft_output.get("status", "unknown"),
            "agent_note": draft_output.get("agent_note", ""),
            "email_subject": draft_output.get("email_subject"),
            "email_draft": draft_output.get("email_draft"),
            "quality_score": draft_output.get("quality_score"),
            "quality_issues": draft_output.get("quality_issues"),
            "selected_signal": draft_output.get("draft_signal_claim"),
            "solution_fit_type": draft_output.get("draft_solution_fit_type"),
            "signal_source_quality": draft_output.get("draft_signal_source_quality"),
            "system_worthiness": draft_output.get("draft_system_worthiness"),
            "why_not_chatgpt_task": draft_output.get("draft_why_not_chatgpt_task"),
            "draft_repair_count": draft_output.get("draft_repair_count"),
            "draft_repair_reason": draft_output.get("draft_repair_reason"),
            "enrichment_result": enrichment_dict,
        }

    def revise_enriched_draft(
        self,
        lead: LeadRow,
        run_id: str,
    ) -> dict[str, Any]:
        enrichment_dict = _parse_enrichment_result(lead.enrichment_result)
        previous_draft = lead.revised_draft or lead.email_draft
        if not enrichment_dict:
            return {
                "lead_id": lead.lead_id,
                "status": "error",
                "agent_note": "enrichment_result is required for enriched revise.",
            }
        if not previous_draft:
            return {
                "lead_id": lead.lead_id,
                "status": "error",
                "agent_note": "email_draft or revised_draft is required for enriched revise.",
            }
        if not lead.revision_instruction:
            return {
                "lead_id": lead.lead_id,
                "status": "error",
                "agent_note": "revision_instruction is required for enriched revise.",
            }

        evidence_items = enrichment_dict.get("evidence_items") or []
        state: LeadState = {
            "run_id": run_id,
            "lead_id": lead.lead_id,
            "action": "revise",
            "lead": lead.model_dump(mode="json"),
            "enrichment_result": enrichment_dict,
            "evidence_items": evidence_items,
            "email_draft": lead.email_draft or "",
            "previous_draft": previous_draft,
            "revision_instruction": lead.revision_instruction,
            "last_processed_revision_hash": lead.last_processed_revision_hash,
            "revision_count": lead.revision_count,
        }
        output = self.revise_graph.invoke(
            state,
            config={"configurable": {"thread_id": f"revise-{lead.lead_id}"}},
        )
        return {
            "lead_id": lead.lead_id,
            "status": output.get("status", "unknown"),
            "agent_note": output.get("agent_note", ""),
            "email_draft": output.get("email_draft"),
            "revised_draft": output.get("revised_draft"),
            "quality_score": output.get("quality_score"),
            "quality_issues": output.get("quality_issues"),
            "selected_signal": output.get("draft_signal_claim"),
            "solution_fit_type": output.get("draft_solution_fit_type"),
            "signal_source_quality": output.get("draft_signal_source_quality"),
            "system_worthiness": output.get("draft_system_worthiness"),
            "why_not_chatgpt_task": output.get("draft_why_not_chatgpt_task"),
            "draft_repair_count": output.get("draft_repair_count"),
            "draft_repair_reason": output.get("draft_repair_reason"),
            "revision_instruction_hash": output.get("revision_instruction_hash"),
            "last_processed_revision_hash": output.get("last_processed_revision_hash"),
            "revision_count": output.get("revision_count"),
            "enrichment_result": enrichment_dict,
        }

    def draft_from_existing_enrichment(
        self,
        lead: LeadRow,
        run_id: str,
    ) -> dict[str, Any]:
        enrichment_dict = _parse_enrichment_result(lead.enrichment_result)
        readiness = validate_readiness(lead)
        if not readiness.ready_for_enrichment:
            status = (
                "discarded"
                if readiness.icp_status == "disqualified"
                else "needs_manual_research"
            )
            return {
                "lead_id": lead.lead_id,
                "status": status,
                "agent_note": (
                    "Draft blocked before generation. "
                    f"{readiness.identity_validation_status}: "
                    f"{readiness.identity_validation_reason}; "
                    f"{readiness.icp_status}: {readiness.icp_score_reason}"
                ),
                "enrichment_result": enrichment_dict,
                **readiness.as_update(),
            }

        if not enrichment_dict:
            return {
                "lead_id": lead.lead_id,
                "status": "needs_manual_research",
                "agent_note": "Draft blocked: enrichment_result is required.",
                **readiness.as_update(),
            }

        try:
            enrichment_result = EnrichmentResult.model_validate(enrichment_dict)
        except Exception as exc:
            return {
                "lead_id": lead.lead_id,
                "status": "error",
                "agent_note": f"Draft blocked: invalid enrichment_result: {exc}",
                **readiness.as_update(),
            }
        enrichment_result.user_decision = lead.user_decision
        enrichment_result.user_decision_notes = lead.user_decision_notes
        enrichment_result = apply_review_decision(enrichment_result)
        enrichment_dict = enrichment_result.model_dump(mode="json")

        if (
            enrichment_result.review_required
            and enrichment_result.user_decision != APPROVE_EXCEPTION
        ):
            return {
                "lead_id": lead.lead_id,
                "status": "needs_manual_research",
                "agent_note": (
                    "Draft blocked: review required. "
                    f"{enrichment_result.review_summary or ''}"
                ).strip(),
                "enrichment_result": enrichment_dict,
                "review_required": enrichment_result.review_required,
                "review_category": enrichment_result.review_category,
                "review_summary": enrichment_result.review_summary,
                "review_evidence": enrichment_result.review_evidence,
                "suggested_action": enrichment_result.suggested_action,
                "suggested_action_reason": enrichment_result.suggested_action_reason,
                **{**readiness.as_update(), "ready_for_draft": False},
            }

        if enrichment_result.recommended_action.value != "draft":
            status = (
                "discarded"
                if enrichment_result.recommended_action.value == "discard"
                else enrichment_result.recommended_action.value
            )
            return {
                "lead_id": lead.lead_id,
                "status": status,
                "agent_note": (
                    "Draft blocked: enrichment recommended "
                    f"{enrichment_result.recommended_action.value}."
                ),
                "enrichment_result": enrichment_dict,
                **readiness.as_update(),
            }

        if (
            enrichment_result.confidence_score is not None
            and enrichment_result.confidence_score < 65
        ):
            return {
                "lead_id": lead.lead_id,
                "status": "needs_manual_research",
                "agent_note": (
                    f"Draft blocked: confidence too low ({enrichment_result.confidence_score})."
                ),
                "enrichment_result": enrichment_dict,
                **readiness.as_update(),
            }

        if not enrichment_result.evidence_items:
            return {
                "lead_id": lead.lead_id,
                "status": "needs_manual_research",
                "agent_note": "Draft blocked: no evidence items.",
                "enrichment_result": enrichment_dict,
                **readiness.as_update(),
            }

        draft_state: LeadState = {
            "run_id": run_id,
            "lead_id": lead.lead_id,
            "action": "draft",
            "lead": lead.model_dump(mode="json"),
            "enrichment_result": enrichment_dict,
        }
        draft_output = self.draft_graph.invoke(
            draft_state,
            config={"configurable": {"thread_id": f"draft-{lead.lead_id}"}},
        )
        return {
            "lead_id": lead.lead_id,
            "status": draft_output.get("status", "unknown"),
            "agent_note": draft_output.get("agent_note", ""),
            "email_subject": draft_output.get("email_subject"),
            "email_draft": draft_output.get("email_draft"),
            "quality_score": draft_output.get("quality_score"),
            "quality_issues": draft_output.get("quality_issues"),
            "selected_signal": draft_output.get("draft_signal_claim"),
            "solution_fit_type": draft_output.get("draft_solution_fit_type"),
            "signal_source_quality": draft_output.get("draft_signal_source_quality"),
            "system_worthiness": draft_output.get("draft_system_worthiness"),
            "why_not_chatgpt_task": draft_output.get("draft_why_not_chatgpt_task"),
            "draft_repair_count": draft_output.get("draft_repair_count"),
            "draft_repair_reason": draft_output.get("draft_repair_reason"),
            "enrichment_result": enrichment_dict,
            **{
                **readiness.as_update(),
                "ready_for_draft": bool(draft_output.get("email_draft"))
                and draft_output.get("status")
                not in {"needs_manual_research", "insufficient_data", "error"},
            },
        }


def _parse_enrichment_result(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}
