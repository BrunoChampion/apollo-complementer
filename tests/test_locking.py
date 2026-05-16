from datetime import UTC, datetime, timedelta

from app.integrations.sheets.base import SheetRow
from app.integrations.sheets.fake import FakeSheetClient
from app.services.locking import acquire_row_lock, lock_is_expired
from app.services.row_selector import PendingLead, select_pending_rows


def test_lock_expiry_detects_stale_locks() -> None:
    now = datetime(2026, 5, 3, 12, 0, tzinfo=UTC)
    old_lock = (now - timedelta(minutes=31)).isoformat()
    fresh_lock = (now - timedelta(minutes=5)).isoformat()

    assert lock_is_expired(old_lock, now=now, expiry_minutes=30) is True
    assert lock_is_expired(fresh_lock, now=now, expiry_minutes=30) is False
    assert lock_is_expired(None, now=now, expiry_minutes=30) is False


def test_selector_recovers_expired_processing_rows() -> None:
    now = datetime.now(UTC)
    expired = (now - timedelta(minutes=45)).isoformat()
    fresh = (now - timedelta(minutes=5)).isoformat()
    rows = [
        SheetRow(
            row_number=2,
            values={
                "lead_id": "expired",
                "company_name": "Expired Lock Co",
                "action": "research_and_draft",
                "status": "processing",
                "locked_at": expired,
            },
        ),
        SheetRow(
            row_number=3,
            values={
                "lead_id": "fresh",
                "company_name": "Fresh Lock Co",
                "action": "research_and_draft",
                "status": "processing",
                "locked_at": fresh,
            },
        ),
    ]

    pending = select_pending_rows(rows, lock_expiry_minutes=30)

    assert [item.lead.lead_id for item in pending] == ["expired"]


def test_acquire_row_lock_rejects_fresh_processing_lock() -> None:
    now = datetime.now(UTC)
    pending = PendingLead(
        row_number=2,
        lead=select_pending_rows(
            [
                SheetRow(
                    row_number=2,
                    values={
                        "lead_id": "locked",
                        "company_name": "Locked Co",
                        "action": "research_and_draft",
                        "status": "processing",
                        "locked_at": (now - timedelta(minutes=5)).isoformat(),
                    },
                )
            ],
            lock_expiry_minutes=1,
        )[0].lead,
    )
    client = FakeSheetClient("tests/fixtures/leads_sample.csv")

    result = acquire_row_lock(
        sheet_client=client,
        pending=pending,
        run_id="run_new",
        now=now,
        expiry_minutes=30,
    )

    assert result.acquired is False
    assert result.reason == "row is already locked"
