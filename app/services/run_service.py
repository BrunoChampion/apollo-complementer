from typing import Any

from app.core.config import get_settings
from app.core.langfuse import Tracer, get_tracer
from app.core.limits import BatchLimits, get_batch_limits
from app.db.models import Run
from app.db.repositories import RunRepository
from app.domain.leads import LeadAction, LeadStatus
from app.graph.builder import build_research_and_draft_graph
from app.graph.llm_factory import build_draft_llm
from app.integrations.gmail import GmailClient, GmailClientProtocol
from app.integrations.sheets.base import SheetClient
from app.integrations.sheets.factory import build_sheet_client
from app.services.email_summary import EmailSender, send_run_summary_email
from app.services.locking import acquire_row_lock
from app.services.row_selector import (
    PendingLead,
    RejectedLeadRow,
    select_pending_rows_with_rejections,
)
from app.services.sheet_activity_log import record_email_draft_activity, record_run_activity

SHEET_OUTPUT_COLUMNS = {
    "status",
    "fit_score",
    "fit_score_reason",
    "quality_score",
    "quality_issues",
    "evidence_quality",
    "manual_context_summary",
    "message_angle",
    "email_subject",
    "email_draft",
    "revision_instruction_hash",
    "last_processed_revision_hash",
    "revision_count",
    "revised_draft",
    "agent_note",
    "error_message",
    "run_id",
    "locked_at",
    "processed_at",
    "last_updated_by_agent_at",
}


class RunService:
    def __init__(self, repository: RunRepository) -> None:
        self.repository = repository

    def create_run(
        self,
        *,
        source: str,
        sheet_id: str | None = None,
        created_by: str | None = None,
    ) -> Run:
        return self.repository.create_run(
            source=source,
            sheet_id=sheet_id,
            created_by=created_by,
        )

    def process_run(
        self,
        run_id: str,
        *,
        sheet_path: str,
        source: str = "fake_sheet",
        sheet_id: str | None = None,
        tab_name: str | None = None,
        sheet_client: SheetClient | None = None,
        gmail_client: GmailClientProtocol | None = None,
        tracer: Tracer | None = None,
        email_sender: EmailSender | None = None,
        scheduled: bool = False,
        limits: BatchLimits | None = None,
    ) -> Run:
        self.repository.update_run_status(run_id, "running")
        settings = get_settings()
        tracer = tracer or get_tracer(settings)
        limits = limits or get_batch_limits(settings)
        graph = build_research_and_draft_graph(llm=build_draft_llm(settings))
        batch_limit = limits.scheduled_batch_limit if scheduled else limits.manual_run_limit
        with tracer.span(
            "run.process",
            metadata={
                "run_id": run_id,
                "source": source,
                "sheet_id": sheet_id,
                "sheet_path": sheet_path,
                "scheduled": scheduled,
                "batch_limit": batch_limit,
            },
        ):
            sheet_client = sheet_client or build_sheet_client(
                source=source,
                sheet_path=sheet_path,
                sheet_id=sheet_id,
                tab_name=tab_name,
            )
            rows = sheet_client.read_rows()
            pending_rows, rejected_rows = select_pending_rows_with_rejections(
                rows,
                lock_expiry_minutes=settings.lock_expiry_minutes,
                max_revision_count_without_override=limits.max_revision_count_without_override,
            )
            limited_pending_rows = pending_rows[:batch_limit]

            success_count = 0
            error_count = 0
            drafts_created = 0
            skipped_count = max(0, len(pending_rows) - len(limited_pending_rows))

            for pending in limited_pending_rows:
                result = self._process_pending_row(
                    run_id,
                    sheet_client,
                    pending,
                    gmail_client=gmail_client or GmailClient(),
                    tracer=tracer,
                    lock_expiry_minutes=settings.lock_expiry_minutes,
                    settings=settings,
                    graph=graph,
                )
                if result == "success":
                    success_count += 1
                    if pending.lead.action == LeadAction.CREATE_GMAIL_DRAFT:
                        drafts_created += 1
                elif result == "error":
                    error_count += 1
                else:
                    skipped_count += 1

            for rejected in rejected_rows:
                self._record_rejected_row(run_id, sheet_client, rejected, tracer=tracer)
                error_count += 1

            summary = {
                "sheet_path": sheet_path,
                "pending_rows": [pending.row_number for pending in limited_pending_rows],
                "rejected_rows": [rejected.row_number for rejected in rejected_rows],
                "skipped_due_to_limit": max(0, len(pending_rows) - len(limited_pending_rows)),
                "skipped_count": skipped_count,
                "batch_limit": batch_limit,
            }
            finished_run = self.repository.finish_run(
                run_id,
                status="completed",
                total_rows=success_count + error_count + skipped_count,
                success_count=success_count,
                error_count=error_count,
                summary=summary,
            )
            try:
                send_run_summary_email(finished_run, sender=email_sender, settings=settings)
            except Exception:
                pass
            try:
                record_run_activity(
                    sheet_client=sheet_client,
                    run=finished_run,
                    settings=settings,
                    drafts_created=drafts_created,
                )
            except Exception:
                pass
            return finished_run

    def _process_pending_row(
        self,
        run_id: str,
        sheet_client: SheetClient,
        pending: PendingLead,
        gmail_client: GmailClientProtocol,
        tracer: Tracer,
        lock_expiry_minutes: int,
        settings: Any,
        graph: Any,
    ) -> str:
        metadata = {
            "run_id": run_id,
            "lead_id": pending.lead.lead_id,
            "row_number": pending.row_number,
            "action": pending.lead.action.value,
            "company_name": pending.lead.company_name,
        }
        with tracer.span("row.process", metadata=metadata):
            lock_result = acquire_row_lock(
                sheet_client=sheet_client,
                pending=pending,
                run_id=run_id,
                expiry_minutes=lock_expiry_minutes,
            )
        if not lock_result.acquired:
            self.repository.create_lead_run(
                run_id=run_id,
                lead_id=pending.lead.lead_id,
                row_number=pending.row_number,
                action=pending.lead.action.value,
                status="skipped",
                input_snapshot=pending.lead.model_dump(mode="json"),
                output_snapshot={"skip_reason": lock_result.reason},
                error_message=lock_result.reason,
                finished=True,
            )
            return "skipped"

        if pending.lead.action == LeadAction.CREATE_GMAIL_DRAFT:
            output = self._create_gmail_draft_output(pending, gmail_client)
            output.update({"run_id": run_id, "locked_at": lock_result.locked_at})
            sheet_client.update_row(pending.row_number, output)
            if output["status"] == LeadStatus.GMAIL_DRAFT_CREATED.value:
                try:
                    record_email_draft_activity(
                        sheet_client=sheet_client,
                        run_id=run_id,
                        lead=pending.lead,
                        output=output,
                        settings=settings,
                    )
                except Exception:
                    pass
            status = output["status"]
        else:
            output = self._run_agent_graph(
                graph=graph,
                run_id=run_id,
                pending=pending,
                locked_at=lock_result.locked_at,
            )
            sheet_client.update_row(pending.row_number, _sheet_output(output))
            status = output["status"]

        self.repository.create_lead_run(
            run_id=run_id,
            lead_id=pending.lead.lead_id,
            row_number=pending.row_number,
            action=pending.lead.action.value,
            status=status,
            input_snapshot=pending.lead.model_dump(mode="json"),
            output_snapshot=output,
            error_message=output.get("error_message"),
            finished=True,
        )
        self._record_row_scores(tracer, metadata=metadata, output=output)
        if status == LeadStatus.ERROR.value:
            return "error"
        return "success"

    def _run_agent_graph(
        self,
        *,
        graph: Any,
        run_id: str,
        pending: PendingLead,
        locked_at: str,
    ) -> dict[str, Any]:
        try:
            result = graph.invoke(
                {
                    "run_id": run_id,
                    "lead_id": pending.lead.lead_id,
                    "action": pending.lead.action.value,
                    "lead": pending.lead.model_dump(mode="json"),
                },
                config={"configurable": {"thread_id": f"{run_id}:{pending.lead.lead_id}"}},
            )
        except Exception as exc:
            return {
                "status": LeadStatus.ERROR.value,
                "run_id": run_id,
                "locked_at": locked_at,
                "error_message": f"Agent graph failed: {exc}",
                "agent_note": "Agent graph failed before writing a draft.",
            }

        result.update(
            {
                "run_id": run_id,
                "locked_at": locked_at,
            }
        )
        return result

    def _create_gmail_draft_output(
        self,
        pending: PendingLead,
        gmail_client: GmailClientProtocol,
    ) -> dict[str, Any]:
        lead = pending.lead
        if lead.gmail_draft_id:
            return {
                "status": LeadStatus.GMAIL_DRAFT_CREATED.value,
                "gmail_draft_id": lead.gmail_draft_id,
                "gmail_draft_url": lead.gmail_draft_url,
                "agent_note": "Gmail draft already exists; skipped duplicate creation.",
            }
        if not lead.prospect_email:
            return {
                "status": LeadStatus.ERROR.value,
                "error_message": "prospect_email is required to create a Gmail draft",
            }

        body = lead.final_message or lead.revised_draft or lead.email_draft
        if not body:
            return {
                "status": LeadStatus.ERROR.value,
                "error_message": "final_message, revised_draft or email_draft is required",
            }

        subject = lead.final_subject or lead.email_subject or f"Idea para {lead.company_name}"
        try:
            draft = gmail_client.create_draft(to=lead.prospect_email, subject=subject, body=body)
        except Exception as exc:
            return {
                "status": LeadStatus.ERROR.value,
                "error_message": f"Gmail draft creation failed: {exc}",
            }
        return {
            "status": LeadStatus.GMAIL_DRAFT_CREATED.value,
            "gmail_draft_id": draft.gmail_draft_id,
            "gmail_draft_url": draft.gmail_draft_url,
            "agent_note": "Gmail draft created for human review.",
        }

    def _record_rejected_row(
        self,
        run_id: str,
        sheet_client: SheetClient,
        rejected: RejectedLeadRow,
        tracer: Tracer,
    ) -> None:
        lead_id = str(rejected.values.get("lead_id") or f"row_{rejected.row_number}")
        metadata = {
            "run_id": run_id,
            "lead_id": lead_id,
            "row_number": rejected.row_number,
            "action": str(rejected.values.get("action") or "unknown"),
            "status": "error",
        }
        output: dict[str, Any] = {
            "status": "error",
            "run_id": run_id,
            "error_message": rejected.error_message,
        }
        with tracer.span("row.error", metadata=metadata):
            sheet_client.update_row(rejected.row_number, output)
        self.repository.create_lead_run(
            run_id=run_id,
            lead_id=lead_id,
            row_number=rejected.row_number,
            action=str(rejected.values.get("action") or "unknown"),
            status="error",
            input_snapshot=dict(rejected.values),
            output_snapshot=output,
            error_message=rejected.error_message,
            finished=True,
        )

    def _record_row_scores(
        self,
        tracer: Tracer,
        *,
        metadata: dict[str, Any],
        output: dict[str, Any],
    ) -> None:
        for score_name in ("quality_score", "fit_score"):
            score_value = output.get(score_name)
            if isinstance(score_value, (int, float)):
                tracer.score(name=score_name, value=float(score_value), metadata=metadata)


def _sheet_output(output: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, value in output.items():
        if key in SHEET_OUTPUT_COLUMNS:
            if key == "quality_issues" and isinstance(value, list):
                values[key] = "; ".join(str(item) for item in value)
            else:
                values[key] = value
    return values
