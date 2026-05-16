import logging
from typing import Any

from app.domain.leads import LeadRow, LeadStatus
from app.graph.enrichment_builder import build_enrichment_graph
from app.integrations.sheets.base import SheetClient
from app.integrations.sheets.constants import ENRICHMENT_TAB, LEADS_TAB
from app.services.enrich_and_draft_service import _parse_enrichment_result
from app.services.enrichment_sheet_writer import EnrichmentSheetWriter
from app.services.readiness import validate_readiness

logger = logging.getLogger(__name__)


class LeadEnrichmentService:
    """Enrich leads from the Leads tab using the enrichment graph."""

    def __init__(self, sheet_client: SheetClient) -> None:
        self.sheet_client = sheet_client
        self.graph = build_enrichment_graph()
        self.sheet_writer = EnrichmentSheetWriter(sheet_client)

    def enrich_leads(
        self,
        lead_ids: list[str] | None = None,
        run_id: str = "manual",
        force: bool = False,
    ) -> list[dict[str, Any]]:
        logger.info(
            "enrichment.run.start run_id=%s selected_leads=%s force=%s",
            run_id,
            len(lead_ids) if lead_ids else "all",
            force,
        )
        rows = self.sheet_client.read_rows(tab_name=LEADS_TAB)
        existing_enrichment_ids = self._existing_enrichment_ids()
        logger.info("enrichment.run.rows_loaded run_id=%s rows=%s", run_id, len(rows))
        results = []

        for row in rows:
            values = dict(row.values)
            if not values.get("lead_id"):
                continue
            if lead_ids and values.get("lead_id") not in lead_ids:
                continue

            try:
                lead = LeadRow.model_validate(values)
            except Exception as exc:
                logger.info(
                    "enrichment.run.skip_invalid_row row_number=%s error=%s",
                    row.row_number,
                    exc,
                )
                continue

            # Only enrich leads that are pending or new
            valid_statuses = {
                LeadStatus.NEW,
                LeadStatus.ENRICHMENT_PENDING,
                LeadStatus.ENRICHED,
                LeadStatus.READY_FOR_ENRICHMENT,
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
                        "enrichment.run.backfilled_enrichment_tab "
                        "run_id=%s lead_id=%s enrichment_id=%s status=%s",
                        run_id,
                        lead.lead_id,
                        enrichment_id,
                        lead.status.value,
                    )
                logger.info(
                    "enrichment.run.skip_status run_id=%s lead_id=%s status=%s",
                    run_id,
                    lead.lead_id,
                    lead.status.value,
                )
                continue
            if should_retry_missing_enrichment:
                logger.info(
                    "enrichment.run.retry_missing_enrichment_result "
                    "run_id=%s lead_id=%s status=%s",
                    run_id,
                    lead.lead_id,
                    lead.status.value,
                )
            if force:
                logger.info(
                    "enrichment.run.force_reprocess "
                    "run_id=%s lead_id=%s previous_status=%s",
                    run_id,
                    lead.lead_id,
                    lead.status.value,
                )

            readiness = validate_readiness(lead)
            readiness_update = readiness.as_update()
            if not readiness.ready_for_enrichment:
                blocked_status = (
                    LeadStatus.DISCARDED.value
                    if readiness.icp_status == "disqualified"
                    else LeadStatus.NEEDS_MANUAL_RESEARCH.value
                )
                self.sheet_client.update_row(
                    row_number=row.row_number,
                    values={
                        **readiness_update,
                        "status": blocked_status,
                        "agent_note": (
                            "Enrichment blocked before web research. "
                            f"{readiness.identity_validation_status}: "
                            f"{readiness.identity_validation_reason}; "
                            f"{readiness.icp_status}: {readiness.icp_score_reason}"
                        ),
                    },
                    tab_name=LEADS_TAB,
                )
                results.append(
                    {
                        "lead_id": lead.lead_id,
                        "status": blocked_status,
                        "agent_note": "Enrichment blocked by LinkedIn/ICP readiness gate.",
                    }
                )
                logger.info(
                    "enrichment.run.blocked_readiness run_id=%s lead_id=%s identity=%s icp=%s",
                    run_id,
                    lead.lead_id,
                    readiness.identity_validation_status,
                    readiness.icp_status,
                )
                continue

            logger.info(
                "enrichment.run.lead_start run_id=%s lead_id=%s company=%s country=%s",
                run_id,
                lead.lead_id,
                lead.company_name,
                lead.country,
            )
            state = {
                "run_id": run_id,
                "lead_id": lead.lead_id,
                "lead": lead.model_dump(mode="json"),
            }
            output = self.graph.invoke(
                state,
                config={"configurable": {"thread_id": f"enrich-{lead.lead_id}"}},
            )

            result_dict = output.get("enrichment_result", {})
            if result_dict:
                self.sheet_writer.append(result_dict)
                # Update lead status in sheet
                new_status = result_dict.get("enrichment_status", "needs_review")
                ready_for_draft = (
                    result_dict.get("recommended_action") == "draft"
                    and not result_dict.get("review_required")
                )
                self.sheet_client.update_row(
                    row_number=row.row_number,
                    values={
                        **readiness_update,
                        "ready_for_enrichment": True,
                        "ready_for_draft": ready_for_draft,
                        "review_required": result_dict.get("review_required"),
                        "review_category": result_dict.get("review_category"),
                        "review_summary": result_dict.get("review_summary"),
                        "review_evidence": result_dict.get("review_evidence"),
                        "suggested_action": result_dict.get("suggested_action"),
                        "suggested_action_reason": result_dict.get("suggested_action_reason"),
                        "status": new_status,
                        "agent_note": output.get("agent_note", ""),
                        "enrichment_result": result_dict,
                    },
                    tab_name=LEADS_TAB,
                )
                logger.info(
                    "enrichment.run.lead_done "
                    "run_id=%s lead_id=%s status=%s action=%s confidence=%s",
                    run_id,
                    lead.lead_id,
                    new_status,
                    result_dict.get("recommended_action"),
                    result_dict.get("confidence_score"),
                )

            results.append({
                "lead_id": lead.lead_id,
                "status": output.get("status", "unknown"),
                "agent_note": output.get("agent_note", ""),
                "enrichment_result": result_dict,
            })

        logger.info(
            "enrichment.run.done run_id=%s processed=%s",
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
