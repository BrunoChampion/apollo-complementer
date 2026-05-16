import shutil
from pathlib import Path

from app.db.repositories import RunRepository
from app.services.email_summary import render_run_summary_email
from app.services.run_service import RunService
from tests.db_utils import build_test_session

WORKING_EMAIL = Path("tests/fixtures/leads_email_working.csv")


class FakeEmailSender:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def send(self, *, to_email: str, subject: str, body: str) -> None:
        self.messages.append({"to_email": to_email, "subject": subject, "body": body})


def test_render_run_summary_email_includes_counts_and_rows() -> None:
    session = next(build_test_session())
    repository = RunRepository(session)
    run = repository.create_run(source="fake_sheet", sheet_id="examples/leads_demo.csv")
    finished = repository.finish_run(
        run.id,
        status="completed",
        total_rows=4,
        success_count=3,
        error_count=1,
        summary={
            "sheet_path": "examples/leads_demo.csv",
            "pending_rows": [2, 4, 6],
            "rejected_rows": [8],
            "skipped_count": 0,
            "batch_limit": 10,
        },
    )

    rendered = render_run_summary_email(finished, to_email="ops@example.com")

    assert rendered.to_email == "ops@example.com"
    assert rendered.subject == "Revenue Copilot: 4 filas procesadas, 3 OK, 1 errores"
    assert f"Run ID: {run.id}" in rendered.body
    assert "Successes: 3" in rendered.body
    assert "Rejected rows: 8" in rendered.body


def test_run_service_sends_summary_email_after_completion() -> None:
    shutil.copyfile("tests/fixtures/leads_sample.csv", WORKING_EMAIL)
    session = next(build_test_session())
    repository = RunRepository(session)
    service = RunService(repository)
    sender = FakeEmailSender()
    run = service.create_run(
        source="fake_sheet",
        sheet_id=str(WORKING_EMAIL),
        created_by="seller@example.com",
    )

    try:
        service.process_run(
            run.id,
            sheet_path=str(WORKING_EMAIL),
            email_sender=sender,
        )

        assert len(sender.messages) == 1
        assert sender.messages[0]["to_email"] == "seller@example.com"
        assert "Revenue Copilot:" in sender.messages[0]["subject"]
        assert f"Run ID: {run.id}" in sender.messages[0]["body"]
    finally:
        if WORKING_EMAIL.exists():
            WORKING_EMAIL.unlink()
