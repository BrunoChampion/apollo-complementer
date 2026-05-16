import csv
import shutil
from pathlib import Path

from app.db.repositories import RunRepository
from app.integrations.gmail import GmailDraft
from app.services.run_service import RunService
from tests.db_utils import build_test_session

WORKING_GMAIL = Path("tests/fixtures/leads_gmail_working.csv")


class FakeGmailClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def create_draft(self, *, to: str, subject: str, body: str) -> GmailDraft:
        self.calls.append({"to": to, "subject": subject, "body": body})
        return GmailDraft(
            gmail_draft_id="draft_123",
            gmail_draft_url="https://mail.google.com/mail/u/0/#drafts/draft_123",
        )


def test_run_service_creates_gmail_draft_for_approved_row() -> None:
    shutil.copyfile("tests/fixtures/leads_sample.csv", WORKING_GMAIL)
    session = next(build_test_session())
    repository = RunRepository(session)
    service = RunService(repository)
    run = service.create_run(source="fake_sheet", sheet_id=str(WORKING_GMAIL))
    gmail = FakeGmailClient()

    try:
        finished = service.process_run(
            run.id,
            sheet_path=str(WORKING_GMAIL),
            gmail_client=gmail,
        )

        with WORKING_GMAIL.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        gmail_row = next(row for row in rows if row["lead_id"] == "lead_gmail_001")

        assert finished.success_count == 3
        assert gmail.calls == [
            {
                "to": "sofia@opsbridge.example.com",
                "subject": "Idea para OpsBridge",
                "body": "Final aprobado.",
            }
        ]
        assert gmail_row["status"] == "gmail_draft_created"
        assert gmail_row["gmail_draft_id"] == "draft_123"
        assert gmail_row["gmail_draft_url"].endswith("draft_123")
    finally:
        if WORKING_GMAIL.exists():
            WORKING_GMAIL.unlink()
