from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.domain.leads import LeadStatus
from app.integrations.sheets.base import SheetClient

if TYPE_CHECKING:
    from app.services.row_selector import PendingLead


@dataclass(frozen=True)
class LockResult:
    acquired: bool
    locked_at: str | None = None
    reason: str | None = None


def lock_is_expired(
    locked_at: str | None,
    *,
    now: datetime | None = None,
    expiry_minutes: int = 30,
) -> bool:
    if not locked_at:
        return False
    now = now or datetime.now(UTC)
    try:
        locked_at_dt = datetime.fromisoformat(locked_at)
    except ValueError:
        return True
    if locked_at_dt.tzinfo is None:
        locked_at_dt = locked_at_dt.replace(tzinfo=UTC)
    return locked_at_dt <= now - timedelta(minutes=expiry_minutes)


def can_lock_pending_lead(
    pending: "PendingLead",
    *,
    now: datetime | None = None,
    expiry_minutes: int = 30,
) -> bool:
    lead = pending.lead
    if lead.status != LeadStatus.PROCESSING:
        return True
    return lock_is_expired(lead.locked_at, now=now, expiry_minutes=expiry_minutes)


def acquire_row_lock(
    *,
    sheet_client: SheetClient,
    pending: "PendingLead",
    run_id: str,
    now: datetime | None = None,
    expiry_minutes: int = 30,
) -> LockResult:
    now = now or datetime.now(UTC)
    if not can_lock_pending_lead(pending, now=now, expiry_minutes=expiry_minutes):
        return LockResult(acquired=False, reason="row is already locked")

    locked_at = now.isoformat()
    sheet_client.update_row(
        pending.row_number,
        {
            "status": LeadStatus.PROCESSING.value,
            "run_id": run_id,
            "locked_at": locked_at,
        },
    )
    return LockResult(acquired=True, locked_at=locked_at)
