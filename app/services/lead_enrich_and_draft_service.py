import json
import logging
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from app.domain.leads import LeadAction, LeadRow, LeadStatus
from app.integrations.sheets.base import SheetClient
from app.integrations.sheets.constants import (
    EMAIL_DRAFTS_HEADERS,
    EMAIL_DRAFTS_TAB,
    ENRICHMENT_TAB,
    LEADS_TAB,
)
from app.services.enrich_and_draft_service import (
    EnrichAndDraftService,
    _parse_enrichment_result,
)
from app.services.enrichment_sheet_writer import EnrichmentSheetWriter

logger = logging.getLogger(__name__)


class LeadEnrichAndDraftService:
    """Enrich and draft for leads from the Leads tab."""

    def __init__(self, sheet_client: SheetClient) -> None:
        self.sheet_client = sheet_client
        self.service = EnrichAndDraftService()
        self.sheet_writer = EnrichmentSheetWriter(sheet_client)

    def enrich_and_draft_leads(
        self,
        lead_ids: list[str] | None = None,
        run_id: str = "manual",
        force: bool = False,
    ) -> list[dict[str, Any]]:
        logger.info(
            "enrich_and_draft.run.start run_id=%s selected_leads=%s force=%s",
            run_id,
            len(lead_ids) if lead_ids else "all",
            force,
        )
        rows = self.sheet_client.read_rows(tab_name=LEADS_TAB)
        existing_enrichment_ids = self._existing_enrichment_ids()
        logger.info(
            "enrich_and_draft.run.rows_loaded run_id=%s rows=%s",
            run_id,
            len(rows),
        )
        results = []

        for row in rows:
            values = dict(row.values)
            if not values.get("lead_id"):
                continue
            if lead_ids and values.get("lead_id") not in lead_ids:
                continue

            try:
                _drop_blank_enum_defaults(values)
                lead = LeadRow.model_validate(values)
            except Exception as exc:
                logger.info(
                    "enrich_and_draft.run.skip_invalid_row row_number=%s error=%s",
                    row.row_number,
                    exc,
                )
                continue

            valid_statuses = {
                LeadStatus.NEW,
                LeadStatus.ENRICHMENT_PENDING,
                LeadStatus.ENRICHED,
                LeadStatus.READY_FOR_ENRICHMENT,
                LeadStatus.READY_FOR_DRAFT,
            }
            should_retry_missing_enrichment = (
                lead.status
                in {
                    LeadStatus.NEEDS_MANUAL_RESEARCH,
                    LeadStatus.INSUFFICIENT_DATA,
                    LeadStatus.DISCARDED,
                    LeadStatus.ERROR,
                }
                and not _parse_enrichment_result(lead.enrichment_result)
            )
            if (
                not force
                and lead.status not in valid_statuses
                and not should_retry_missing_enrichment
            ):
                enrichment_result = _parse_enrichment_result(lead.enrichment_result)
                enrichment_id = enrichment_result.get("enrichment_id")
                if enrichment_result and enrichment_id not in existing_enrichment_ids:
                    self.sheet_writer.append(enrichment_result)
                    existing_enrichment_ids.add(enrichment_id)
                    logger.info(
                        "enrich_and_draft.run.backfilled_enrichment_tab "
                        "run_id=%s lead_id=%s enrichment_id=%s status=%s",
                        run_id,
                        lead.lead_id,
                        enrichment_id,
                        lead.status.value,
                    )
                logger.info(
                    "enrich_and_draft.run.skip_status run_id=%s lead_id=%s status=%s",
                    run_id,
                    lead.lead_id,
                    lead.status.value,
                )
                continue
            if should_retry_missing_enrichment:
                logger.info(
                    "enrich_and_draft.run.retry_missing_enrichment_result "
                    "run_id=%s lead_id=%s status=%s",
                    run_id,
                    lead.lead_id,
                    lead.status.value,
                )
            if force:
                logger.info(
                    "enrich_and_draft.run.force_reprocess "
                    "run_id=%s lead_id=%s previous_status=%s",
                    run_id,
                    lead.lead_id,
                    lead.status.value,
                )

            logger.info(
                "enrich_and_draft.run.lead_start "
                "run_id=%s lead_id=%s company=%s country=%s note=agent_run_may_take_minutes",
                run_id,
                lead.lead_id,
                lead.company_name,
                lead.country,
            )
            result = self.service.enrich_and_draft(lead, run_id=run_id)
            if result.get("enrichment_result"):
                self.sheet_writer.append(result["enrichment_result"])

            # Update lead in sheet
            update_values: dict[str, Any] = {
                "status": result.get("status", "unknown"),
                "agent_note": result.get("agent_note", ""),
            }
            for key in (
                "identity_validation_status",
                "identity_validation_reason",
                "icp_status",
                "icp_score",
                "icp_score_reason",
                "ready_for_enrichment",
                "ready_for_draft",
                "review_required",
                "review_category",
                "review_summary",
                "review_evidence",
                "suggested_action",
                "suggested_action_reason",
            ):
                if result.get(key) is not None:
                    update_values[key] = result[key]
            if result.get("enrichment_result"):
                update_values["enrichment_result"] = result["enrichment_result"]
            if result.get("email_subject"):
                update_values["email_subject"] = result["email_subject"]
            if result.get("email_draft"):
                update_values["email_draft"] = result["email_draft"]
            if result.get("quality_score"):
                update_values["quality_score"] = result["quality_score"]

            self.sheet_client.update_row(
                row_number=row.row_number,
                values=update_values,
                tab_name=LEADS_TAB,
            )
            self._append_generated_draft(
                lead=lead,
                result=result,
                run_id=run_id,
            )
            logger.info(
                "enrich_and_draft.run.lead_done "
                "run_id=%s lead_id=%s status=%s draft_created=%s quality_score=%s",
                run_id,
                lead.lead_id,
                result.get("status", "unknown"),
                bool(result.get("email_draft")),
                result.get("quality_score"),
            )

            results.append(result)

        logger.info(
            "enrich_and_draft.run.done run_id=%s processed=%s",
            run_id,
            len(results),
        )
        return results

    def revise_enriched_drafts(
        self,
        lead_ids: list[str] | None = None,
        run_id: str = "manual",
    ) -> list[dict[str, Any]]:
        rows = self.sheet_client.read_rows(tab_name=LEADS_TAB)
        results = []

        for row in rows:
            values = dict(row.values)
            if not values.get("lead_id"):
                continue
            if lead_ids and values.get("lead_id") not in lead_ids:
                continue
            try:
                _drop_blank_enum_defaults(values)
                lead = LeadRow.model_validate(values)
            except Exception:
                continue
            if not _should_revise(lead):
                continue

            result = self.service.revise_enriched_draft(lead, run_id=run_id)
            update_values: dict[str, Any] = {
                "status": result.get("status", "unknown"),
                "agent_note": result.get("agent_note", ""),
            }
            for key in (
                "email_draft",
                "revised_draft",
                "quality_score",
                "quality_issues",
                "revision_instruction_hash",
                "last_processed_revision_hash",
                "revision_count",
            ):
                if result.get(key) is not None:
                    update_values[key] = result[key]

            self.sheet_client.update_row(
                row_number=row.row_number,
                values=update_values,
                tab_name=LEADS_TAB,
            )
            self._append_generated_draft(
                lead=lead,
                result=result,
                run_id=run_id,
            )
            results.append(result)

        return results

    def draft_leads(
        self,
        lead_ids: list[str] | None = None,
        enrichment_ids: list[str] | None = None,
        run_id: str = "manual",
    ) -> list[dict[str, Any]]:
        if enrichment_ids:
            return self._draft_selected_enrichment_rows(
                enrichment_ids=enrichment_ids,
                run_id=run_id,
            )

        logger.info(
            "draft.run.start run_id=%s selected_leads=%s",
            run_id,
            len(lead_ids) if lead_ids else "all",
        )
        rows = self.sheet_client.read_rows(tab_name=LEADS_TAB)
        logger.info(
            "draft.run.rows_loaded run_id=%s rows=%s",
            run_id,
            len(rows),
        )
        results = []
        email_draft_rows_appended = 0

        for row in rows:
            values = dict(row.values)
            if not values.get("lead_id"):
                continue
            if lead_ids and values.get("lead_id") not in lead_ids:
                continue
            try:
                _drop_blank_enum_defaults(values)
                lead = LeadRow.model_validate(values)
            except Exception as exc:
                logger.info(
                    "draft.run.skip_invalid_row row_number=%s error=%s",
                    row.row_number,
                    exc,
                )
                continue

            logger.info(
                "draft.run.lead_start run_id=%s lead_id=%s company=%s status=%s",
                run_id,
                lead.lead_id,
                lead.company_name,
                lead.status.value,
            )
            result = self.service.draft_from_existing_enrichment(lead, run_id=run_id)
            update_values: dict[str, Any] = {
                "status": result.get("status", "unknown"),
                "agent_note": result.get("agent_note", ""),
            }
            for key in (
                "identity_validation_status",
                "identity_validation_reason",
                "icp_status",
                "icp_score",
                "icp_score_reason",
                "ready_for_enrichment",
                "ready_for_draft",
                "review_required",
                "review_category",
                "review_summary",
                "review_evidence",
                "suggested_action",
                "suggested_action_reason",
                "email_subject",
                "email_draft",
                "quality_score",
                "quality_issues",
            ):
                if result.get(key) is not None:
                    update_values[key] = result[key]

            self.sheet_client.update_row(
                row_number=row.row_number,
                values=update_values,
                tab_name=LEADS_TAB,
            )
            if self._append_generated_draft(
                lead=lead,
                result=result,
                run_id=run_id,
            ):
                email_draft_rows_appended += 1
            logger.info(
                "draft.run.lead_done "
                "run_id=%s lead_id=%s status=%s draft_created=%s quality_score=%s",
                run_id,
                lead.lead_id,
                result.get("status", "unknown"),
                bool(result.get("email_draft")),
                result.get("quality_score"),
            )
            results.append(result)

        logger.info(
            "draft.run.done run_id=%s processed=%s email_draft_rows_appended=%s",
            run_id,
            len(results),
            email_draft_rows_appended,
        )
        return results

    def _draft_selected_enrichment_rows(
        self,
        *,
        enrichment_ids: list[str],
        run_id: str,
    ) -> list[dict[str, Any]]:
        logger.info(
            "draft.run.start run_id=%s selected_enrichment_ids=%s source_tab=%s",
            run_id,
            len(enrichment_ids),
            ENRICHMENT_TAB,
        )
        enrichment_rows = self.sheet_client.read_rows(tab_name=ENRICHMENT_TAB)
        lead_rows = self.sheet_client.read_rows(tab_name=LEADS_TAB)
        leads_by_id = {
            str(row.values.get("lead_id")): row
            for row in lead_rows
            if row.values.get("lead_id")
        }
        enrichment_by_id = {
            str(row.values.get("enrichment_id")): row
            for row in enrichment_rows
            if row.values.get("enrichment_id")
        }
        results: list[dict[str, Any]] = []
        email_draft_rows_appended = 0

        for enrichment_id in enrichment_ids:
            row = enrichment_by_id.get(enrichment_id)
            if row is None:
                result = {
                    "lead_id": "",
                    "status": "blocked_before_draft",
                    "agent_note": (
                        "Draft blocked: selected enrichment_id was not found in "
                        "the Enrichment tab."
                    ),
                    "source_tab": ENRICHMENT_TAB,
                    "source_enrichment_id": enrichment_id,
                }
                self._append_draft_values(
                    run_id=run_id,
                    values={
                        "lead_id": "",
                        "created_at": datetime.now(UTC).isoformat(),
                        "draft_status": "blocked_before_draft",
                        "review_reason": result["agent_note"],
                        "agent_note": result["agent_note"],
                        "enrichment_id": enrichment_id,
                        "source_enrichment_id": enrichment_id,
                        "source_tab": ENRICHMENT_TAB,
                        "notes": "No draft generated; selected enrichment_id was missing.",
                    },
                )
                results.append(result)
                email_draft_rows_appended += 1
                continue

            row_values = dict(row.values)
            enrichment_dict = _parse_enrichment_result(
                row_values.get("enrichment_result_json")
            )
            source_hash = _stable_hash(enrichment_dict or row_values)
            lead_id = str(row_values.get("lead_id") or "")
            lead_row = leads_by_id.get(lead_id)
            lead_values = dict(lead_row.values) if lead_row else {}
            lead_values.update(
                {
                    "lead_id": lead_id,
                    "company_name": row_values.get("company_name")
                    or lead_values.get("company_name")
                    or "Unknown company",
                    "company_website": row_values.get("company_website")
                    or lead_values.get("company_website"),
                    "company_domain": row_values.get("company_domain")
                    or lead_values.get("company_domain"),
                    "company_linkedin_url": row_values.get("company_linkedin_url")
                    or lead_values.get("company_linkedin_url"),
                    "prospect_name": row_values.get("prospect_name")
                    or lead_values.get("prospect_name"),
                    "prospect_title": row_values.get("prospect_title")
                    or lead_values.get("prospect_title"),
                    "prospect_linkedin_url": row_values.get("prospect_linkedin_url")
                    or lead_values.get("prospect_linkedin_url"),
                    "country": row_values.get("country") or lead_values.get("country"),
                    "industry": row_values.get("industry") or lead_values.get("industry"),
                    "company_size": row_values.get("company_size")
                    or lead_values.get("company_size"),
                    "status": lead_values.get("status") or "enriched",
                    "action": lead_values.get("action") or "draft",
                    "user_decision": row_values.get("user_decision")
                    or lead_values.get("user_decision"),
                    "user_decision_notes": row_values.get("user_decision_notes")
                    or lead_values.get("user_decision_notes"),
                    "enrichment_result": enrichment_dict,
                }
            )

            try:
                _drop_blank_enum_defaults(lead_values)
                lead = LeadRow.model_validate(lead_values)
            except Exception as exc:
                result = {
                    "lead_id": lead_id,
                    "status": "error",
                    "agent_note": (
                        "Draft blocked: invalid lead data for selected enrichment: "
                        f"{exc}"
                    ),
                    "source_tab": ENRICHMENT_TAB,
                    "source_enrichment_id": enrichment_id,
                    "source_enrichment_hash": source_hash,
                }
                self._append_draft_values(
                    run_id=run_id,
                    values={
                        "lead_id": lead_id,
                        "company_name": row_values.get("company_name"),
                        "prospect_name": row_values.get("prospect_name"),
                        "prospect_title": row_values.get("prospect_title"),
                        "created_at": datetime.now(UTC).isoformat(),
                        "draft_status": "blocked_before_draft",
                        "review_reason": result["agent_note"],
                        "agent_note": result["agent_note"],
                        "enrichment_id": enrichment_id,
                        "source_enrichment_id": enrichment_id,
                        "source_enrichment_hash": source_hash,
                        "source_tab": ENRICHMENT_TAB,
                        "notes": (
                            "No draft generated; selected enrichment could not be "
                            "mapped to a valid lead."
                        ),
                    },
                )
                results.append(result)
                email_draft_rows_appended += 1
                continue

            if not enrichment_dict:
                result = {
                    "lead_id": lead.lead_id,
                    "status": "needs_manual_research",
                    "agent_note": (
                        "Draft blocked: selected Enrichment row is missing "
                        "enrichment_result_json. Re-run enrichment for this lead so "
                        "the draft can use exact evidence instead of stale Leads data."
                    ),
                    "enrichment_result": {},
                    "source_tab": ENRICHMENT_TAB,
                    "source_enrichment_id": enrichment_id,
                    "source_enrichment_hash": source_hash,
                }
            else:
                if enrichment_dict.get("enrichment_id") != enrichment_id:
                    result = {
                        "lead_id": lead.lead_id,
                        "status": "needs_manual_research",
                        "agent_note": (
                            "Draft blocked: enrichment_result_json does not match "
                            "the selected enrichment_id."
                        ),
                        "enrichment_result": enrichment_dict,
                        "source_tab": ENRICHMENT_TAB,
                        "source_enrichment_id": enrichment_id,
                        "source_enrichment_hash": source_hash,
                    }
                else:
                    logger.info(
                        "draft.run.lead_start "
                        "run_id=%s lead_id=%s enrichment_id=%s company=%s "
                        "source_tab=%s source_hash=%s",
                        run_id,
                        lead.lead_id,
                        enrichment_id,
                        lead.company_name,
                        ENRICHMENT_TAB,
                        source_hash,
                    )
                    result = self.service.draft_from_existing_enrichment(
                        lead,
                        run_id=run_id,
                    )
                    result.update(
                        {
                            "source_tab": ENRICHMENT_TAB,
                            "source_enrichment_id": enrichment_id,
                            "source_enrichment_hash": source_hash,
                        }
                    )

            if lead_row is not None:
                update_values: dict[str, Any] = {
                    "status": result.get("status", "unknown"),
                    "agent_note": result.get("agent_note", ""),
                }
                for key in (
                    "identity_validation_status",
                    "identity_validation_reason",
                    "icp_status",
                    "icp_score",
                    "icp_score_reason",
                    "ready_for_enrichment",
                    "ready_for_draft",
                    "review_required",
                    "review_category",
                    "review_summary",
                    "review_evidence",
                    "suggested_action",
                    "suggested_action_reason",
                    "email_subject",
                    "email_draft",
                    "quality_score",
                    "quality_issues",
                ):
                    if result.get(key) is not None:
                        update_values[key] = result[key]
                if enrichment_dict:
                    update_values["enrichment_result"] = enrichment_dict
                self.sheet_client.update_row(
                    row_number=lead_row.row_number,
                    values=update_values,
                    tab_name=LEADS_TAB,
                )

            if self._append_generated_draft(
                lead=lead,
                result=result,
                run_id=run_id,
            ):
                email_draft_rows_appended += 1
            logger.info(
                "draft.run.lead_done "
                "run_id=%s lead_id=%s enrichment_id=%s status=%s "
                "draft_created=%s quality_score=%s source_tab=%s source_hash=%s",
                run_id,
                lead.lead_id,
                enrichment_id,
                result.get("status", "unknown"),
                bool(result.get("email_draft")),
                result.get("quality_score"),
                ENRICHMENT_TAB,
                source_hash,
            )
            results.append(result)

        logger.info(
            "draft.run.done run_id=%s processed=%s email_draft_rows_appended=%s source_tab=%s",
            run_id,
            len(results),
            email_draft_rows_appended,
            ENRICHMENT_TAB,
        )
        return results

    def sync_enrichment_results_from_leads(
        self,
        lead_ids: list[str] | None = None,
        run_id: str = "manual",
    ) -> list[dict[str, Any]]:
        """Copy existing Leads.enrichment_result JSON into the Enrichment tab."""

        logger.info(
            "enrichment.sync_from_leads.start run_id=%s selected_leads=%s",
            run_id,
            len(lead_ids) if lead_ids else "all",
        )
        rows = self.sheet_client.read_rows(tab_name=LEADS_TAB)
        existing_enrichment_ids = self._existing_enrichment_ids()
        results = []
        for row in rows:
            values = dict(row.values)
            if not values.get("lead_id"):
                continue
            if lead_ids and values.get("lead_id") not in lead_ids:
                continue

            enrichment_result = _parse_enrichment_result(
                values.get("enrichment_result")
            )
            if not enrichment_result:
                continue
            enrichment_id = enrichment_result.get("enrichment_id")
            if enrichment_id in existing_enrichment_ids:
                logger.info(
                    "enrichment.sync_from_leads.skip_existing "
                    "run_id=%s lead_id=%s enrichment_id=%s",
                    run_id,
                    values.get("lead_id"),
                    enrichment_id,
                )
                continue
            if not enrichment_result.get("run_id"):
                enrichment_result["run_id"] = run_id
            self.sheet_writer.append(enrichment_result)
            if enrichment_id:
                existing_enrichment_ids.add(enrichment_id)
            logger.info(
                "enrichment.sync_from_leads.synced run_id=%s lead_id=%s enrichment_id=%s",
                run_id,
                values.get("lead_id"),
                enrichment_result.get("enrichment_id"),
            )
            results.append({
                "lead_id": values.get("lead_id"),
                "status": "synced",
                "agent_note": "Existing enrichment_result copied to Enrichment tab.",
                "enrichment_result": enrichment_result,
            })

        logger.info(
            "enrichment.sync_from_leads.done run_id=%s processed=%s",
            run_id,
            len(results),
        )
        return results

    def _existing_enrichment_ids(self) -> set[str]:
        try:
            rows = self.sheet_client.read_rows(tab_name=ENRICHMENT_TAB)
        except Exception as exc:
            logger.info("enrichment.existing_ids.unavailable error=%s", exc)
            return set()
        return {
            str(row.values.get("enrichment_id"))
            for row in rows
            if row.values.get("enrichment_id")
        }

    def _append_generated_draft(
        self,
        *,
        lead: LeadRow,
        result: dict[str, Any],
        run_id: str,
    ) -> bool:
        email_draft = result.get("email_draft")
        enrichment_result = _parse_enrichment_result(result.get("enrichment_result"))
        if not email_draft:
            logger.info(
                "draft.email_drafts.audit_no_draft "
                "run_id=%s lead_id=%s status=%s agent_note=%s",
                run_id,
                lead.lead_id,
                result.get("status"),
                result.get("agent_note"),
            )
            self.sheet_client.append_row(
                tab_name=EMAIL_DRAFTS_TAB,
                headers=EMAIL_DRAFTS_HEADERS,
                values={
                    "run_id": run_id,
                    "lead_id": lead.lead_id,
                    "created_at": datetime.now(UTC).isoformat(),
                    "company_name": lead.company_name,
                    "prospect_name": lead.prospect_name,
                    "prospect_title": lead.prospect_title,
                    "prospect_email": lead.prospect_email,
                    "email_subject": "",
                    "email_draft": "",
                    "draft_status": "blocked_before_draft",
                    "review_reason": _review_reason(result),
                    "quality_score": result.get("quality_score"),
                    "quality_issues": result.get("quality_issues"),
                    "agent_note": result.get("agent_note"),
                    "enrichment_id": enrichment_result.get("enrichment_id"),
                    "source_enrichment_id": result.get("source_enrichment_id")
                    or enrichment_result.get("enrichment_id"),
                    "source_enrichment_hash": result.get("source_enrichment_hash"),
                    "source_tab": result.get("source_tab") or LEADS_TAB,
                    "message_brief": result.get("message_brief"),
                    "raw_selected_evidence_claim": result.get("raw_selected_evidence_claim"),
                    "supporting_evidence_ids": result.get("supporting_evidence_ids"),
                    "signal_candidates": result.get("signal_candidates"),
                    "draft_contract_version": result.get("draft_contract_version"),
                    "selected_signal": result.get("selected_signal"),
                    "solution_fit_type": result.get("solution_fit_type"),
                    "signal_source_quality": result.get("signal_source_quality"),
                    "system_worthiness": result.get("system_worthiness"),
                    "why_not_chatgpt_task": result.get("why_not_chatgpt_task"),
                    "draftability_score": result.get("draftability_score"),
                    "outbound_signal_quality": result.get("outbound_signal_quality"),
                    "draft_repair_count": result.get("draft_repair_count"),
                    "draft_repair_reason": result.get("draft_repair_reason"),
                    "gmail_draft_id": "",
                    "gmail_draft_url": "",
                    "approved": False,
                    "sent_manually": "",
                    "sent_at": "",
                    "reply_status": "",
                    "notes": "No draft generated; row added for auditability.",
                },
            )
            logger.info(
                "draft.email_drafts.audit_appended run_id=%s lead_id=%s status=%s",
                run_id,
                lead.lead_id,
                result.get("status"),
            )
            return True
        self.sheet_client.append_row(
            tab_name=EMAIL_DRAFTS_TAB,
            headers=EMAIL_DRAFTS_HEADERS,
            values={
                "run_id": run_id,
                "lead_id": lead.lead_id,
                "created_at": datetime.now(UTC).isoformat(),
                "company_name": lead.company_name,
                "prospect_name": lead.prospect_name,
                "prospect_title": lead.prospect_title,
                "prospect_email": lead.prospect_email,
                "email_subject": result.get("email_subject"),
                "email_draft": email_draft,
                "draft_status": result.get("status"),
                "review_reason": _review_reason(result),
                "quality_score": result.get("quality_score"),
                "quality_issues": result.get("quality_issues"),
                "agent_note": result.get("agent_note"),
                "enrichment_id": enrichment_result.get("enrichment_id"),
                "source_enrichment_id": result.get("source_enrichment_id")
                or enrichment_result.get("enrichment_id"),
                "source_enrichment_hash": result.get("source_enrichment_hash"),
                "source_tab": result.get("source_tab") or LEADS_TAB,
                "message_brief": result.get("message_brief"),
                "raw_selected_evidence_claim": result.get("raw_selected_evidence_claim"),
                "supporting_evidence_ids": result.get("supporting_evidence_ids"),
                "signal_candidates": result.get("signal_candidates"),
                "draft_contract_version": result.get("draft_contract_version"),
                "selected_signal": result.get("selected_signal"),
                "solution_fit_type": result.get("solution_fit_type"),
                "signal_source_quality": result.get("signal_source_quality"),
                "system_worthiness": result.get("system_worthiness"),
                "why_not_chatgpt_task": result.get("why_not_chatgpt_task"),
                "draftability_score": result.get("draftability_score"),
                "outbound_signal_quality": result.get("outbound_signal_quality"),
                "draft_repair_count": result.get("draft_repair_count"),
                "draft_repair_reason": result.get("draft_repair_reason"),
                "gmail_draft_id": "",
                "gmail_draft_url": "",
                "approved": False,
                "sent_manually": "",
                "sent_at": "",
                "reply_status": "",
                "notes": "",
            },
        )
        logger.info(
            "draft.email_drafts.appended run_id=%s lead_id=%s enrichment_id=%s",
            run_id,
            lead.lead_id,
            enrichment_result.get("enrichment_id"),
        )
        return True

    def _append_draft_values(self, *, run_id: str, values: dict[str, Any]) -> None:
        payload = {"run_id": run_id, **values}
        self.sheet_client.append_row(
            tab_name=EMAIL_DRAFTS_TAB,
            headers=EMAIL_DRAFTS_HEADERS,
            values=payload,
        )


def _should_revise(lead: LeadRow) -> bool:
    return bool(
        lead.revision_instruction
        and (
            lead.action == LeadAction.REVISE
            or lead.status == LeadStatus.NEEDS_REVISION
        )
    )


def _stable_hash(value: Any) -> str:
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        raw = str(value)
    return sha256(raw.encode("utf-8")).hexdigest()[:16]


def _drop_blank_enum_defaults(values: dict[str, Any]) -> None:
    for key in ("action", "status"):
        if values.get(key) in {None, ""}:
            values.pop(key, None)


def _review_reason(result: dict[str, Any]) -> str | None:
    issues = result.get("quality_issues")
    if isinstance(issues, list) and issues:
        return "; ".join(str(issue) for issue in issues if issue)
    if isinstance(issues, str) and issues.strip():
        return issues.strip()
    return result.get("agent_note")
