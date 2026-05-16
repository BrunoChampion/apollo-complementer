from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from app.core.config import Settings
from app.db.models import Run
from app.domain.leads import LeadRow

RUN_LOG_HEADERS = [
    "run_id",
    "started_at",
    "finished_at",
    "source",
    "sheet_id",
    "created_by",
    "status",
    "total_rows",
    "success_count",
    "error_count",
    "skipped_count",
    "drafts_created",
    "batch_limit",
    "notes",
]

EMAIL_DRAFT_LOG_HEADERS = [
    "run_id",
    "lead_id",
    "created_at",
    "company_name",
    "prospect_name",
    "prospect_title",
    "prospect_email",
    "email_subject",
    "email_draft",
    "draft_status",
    "quality_score",
    "quality_issues",
    "agent_note",
    "enrichment_id",
    "gmail_draft_id",
    "gmail_draft_url",
    "approved",
    "sent_manually",
    "sent_at",
    "reply_status",
    "notes",
]


class AppendableSheetClient(Protocol):
    def append_row(self, *, tab_name: str, values: dict[str, Any], headers: list[str]) -> None: ...


def record_run_activity(
    *,
    sheet_client: Any,
    run: Run,
    settings: Settings,
    drafts_created: int,
) -> None:
    if not _can_append(sheet_client):
        return
    summary = run.summary or {}
    sheet_client.append_row(
        tab_name=settings.google_sheets_runs_tab,
        headers=RUN_LOG_HEADERS,
        values={
            "run_id": run.id,
            "started_at": _iso(run.started_at),
            "finished_at": _iso(run.finished_at),
            "source": run.source,
            "sheet_id": run.sheet_id,
            "created_by": run.created_by,
            "status": run.status,
            "total_rows": run.total_rows,
            "success_count": run.success_count,
            "error_count": run.error_count,
            "skipped_count": summary.get("skipped_count"),
            "drafts_created": drafts_created,
            "batch_limit": summary.get("batch_limit"),
            "notes": _run_notes(summary),
        },
    )


def record_email_draft_activity(
    *,
    sheet_client: Any,
    run_id: str,
    lead: LeadRow,
    output: dict[str, Any],
    settings: Settings,
) -> None:
    if not _can_append(sheet_client):
        return
    sheet_client.append_row(
        tab_name=settings.google_sheets_email_drafts_tab,
        headers=EMAIL_DRAFT_LOG_HEADERS,
        values={
            "run_id": run_id,
            "lead_id": lead.lead_id,
            "created_at": datetime.now(UTC).isoformat(),
            "company_name": lead.company_name,
            "prospect_name": lead.prospect_name,
            "prospect_title": lead.prospect_title,
            "prospect_email": lead.prospect_email,
            "email_subject": lead.final_subject or lead.email_subject,
            "email_draft": lead.final_message or lead.revised_draft or lead.email_draft,
            "draft_status": lead.status.value,
            "quality_score": lead.quality_score,
            "quality_issues": lead.quality_issues,
            "agent_note": output.get("agent_note"),
            "enrichment_id": "",
            "gmail_draft_id": output.get("gmail_draft_id"),
            "gmail_draft_url": output.get("gmail_draft_url"),
            "approved": lead.approved,
            "sent_manually": "",
            "sent_at": "",
            "reply_status": "",
            "notes": output.get("agent_note"),
        },
    )


def _can_append(sheet_client: Any) -> bool:
    return callable(getattr(sheet_client, "append_row", None))


def _iso(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _run_notes(summary: dict[str, Any]) -> str:
    skipped = summary.get("skipped_due_to_limit", 0)
    rejected = len(summary.get("rejected_rows", []))
    return f"skipped_due_to_limit={skipped}; rejected_rows={rejected}"
