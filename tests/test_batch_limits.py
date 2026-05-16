import csv
import shutil
from pathlib import Path

from app.core.limits import BatchLimits
from app.db.repositories import RunRepository
from app.services.run_service import RunService
from tests.db_utils import build_test_session

WORKING_BATCH = Path("tests/fixtures/leads_batch_working.csv")


def test_manual_run_limit_caps_processed_rows() -> None:
    shutil.copyfile("tests/fixtures/leads_batch.csv", WORKING_BATCH)
    session = next(build_test_session())
    repository = RunRepository(session)
    service = RunService(repository)
    run = service.create_run(source="fake_sheet", sheet_id=str(WORKING_BATCH))

    try:
        finished = service.process_run(
            run.id,
            sheet_path=str(WORKING_BATCH),
            limits=BatchLimits(
                manual_run_limit=3,
                scheduled_batch_limit=50,
                row_timeout_seconds=120,
                max_revision_count_without_override=2,
            ),
        )

        with WORKING_BATCH.open(encoding="utf-8", newline="") as file:
            rows = [row for row in csv.DictReader(file) if row.get("lead_id")]

        assert finished.success_count == 3
        assert finished.summary["skipped_due_to_limit"] == 2
        assert [row["status"] for row in rows[:3]] == ["drafted", "drafted", "drafted"]
        assert [row["status"] for row in rows[3:]] == ["new", "new"]
    finally:
        if WORKING_BATCH.exists():
            WORKING_BATCH.unlink()


def test_scheduled_run_uses_scheduled_batch_limit() -> None:
    shutil.copyfile("tests/fixtures/leads_batch.csv", WORKING_BATCH)
    session = next(build_test_session())
    repository = RunRepository(session)
    service = RunService(repository)
    run = service.create_run(source="fake_sheet", sheet_id=str(WORKING_BATCH))

    try:
        finished = service.process_run(
            run.id,
            sheet_path=str(WORKING_BATCH),
            scheduled=True,
            limits=BatchLimits(
                manual_run_limit=1,
                scheduled_batch_limit=4,
                row_timeout_seconds=120,
                max_revision_count_without_override=2,
            ),
        )

        assert finished.success_count == 4
        assert finished.summary["batch_limit"] == 4
        assert finished.summary["skipped_due_to_limit"] == 1
    finally:
        if WORKING_BATCH.exists():
            WORKING_BATCH.unlink()
