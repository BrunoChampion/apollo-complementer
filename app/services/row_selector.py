from dataclasses import dataclass

from pydantic import ValidationError

from app.domain.leads import LeadAction, LeadRow, LeadStatus
from app.integrations.sheets.base import SheetRow
from app.services.locking import lock_is_expired
from app.services.revision_hash import hash_revision_instruction

PROCESSABLE_ACTIONS = {
    LeadAction.RESEARCH_AND_DRAFT,
    LeadAction.REVISE,
    LeadAction.CREATE_GMAIL_DRAFT,
}


@dataclass(frozen=True)
class PendingLead:
    row_number: int
    lead: LeadRow


@dataclass(frozen=True)
class RejectedLeadRow:
    row_number: int
    values: dict[str, object]
    error_message: str


def select_pending_rows(
    rows: list[SheetRow],
    *,
    lock_expiry_minutes: int = 30,
    max_revision_count_without_override: int = 2,
) -> list[PendingLead]:
    selected, _ = select_pending_rows_with_rejections(
        rows,
        lock_expiry_minutes=lock_expiry_minutes,
        max_revision_count_without_override=max_revision_count_without_override,
    )
    return selected


def select_pending_rows_with_rejections(
    rows: list[SheetRow],
    *,
    lock_expiry_minutes: int = 30,
    max_revision_count_without_override: int = 2,
) -> tuple[list[PendingLead], list[RejectedLeadRow]]:
    selected: list[PendingLead] = []
    rejected: list[RejectedLeadRow] = []

    for row in rows:
        try:
            lead = LeadRow.from_mapping(row.values)
        except ValidationError as exc:
            rejected.append(
                RejectedLeadRow(
                    row_number=row.row_number,
                    values=row.values,
                    error_message=str(exc),
                )
            )
            continue

        if is_pending_lead(
            lead,
            lock_expiry_minutes=lock_expiry_minutes,
            max_revision_count_without_override=max_revision_count_without_override,
        ):
            selected.append(PendingLead(row_number=row.row_number, lead=lead))

    return selected, rejected


def is_pending_lead(
    lead: LeadRow,
    *,
    lock_expiry_minutes: int = 30,
    max_revision_count_without_override: int = 2,
) -> bool:
    if lead.status == LeadStatus.PROCESSING and not lock_is_expired(
        lead.locked_at,
        expiry_minutes=lock_expiry_minutes,
    ):
        return False
    if lead.action not in PROCESSABLE_ACTIONS:
        return False
    if lead.action == LeadAction.REVISE:
        return _revision_needs_processing(
            lead,
            max_revision_count_without_override=max_revision_count_without_override,
        )
    if lead.action == LeadAction.CREATE_GMAIL_DRAFT:
        return (
            lead.approved
            and not lead.gmail_draft_id
            and bool(lead.final_message or lead.revised_draft or lead.email_draft)
        )
    return True


def _revision_needs_processing(
    lead: LeadRow,
    *,
    max_revision_count_without_override: int,
) -> bool:
    if not lead.revision_instruction:
        return False
    if lead.revision_count >= max_revision_count_without_override:
        return False
    current_hash = lead.revision_instruction_hash or hash_revision_instruction(
        lead.revision_instruction
    )
    return current_hash != lead.last_processed_revision_hash
