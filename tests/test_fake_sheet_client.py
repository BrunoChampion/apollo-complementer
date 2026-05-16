import csv
import shutil
from pathlib import Path

from app.integrations.sheets.fake import FakeSheetClient

WORKING_FIXTURE = Path("tests/fixtures/leads_sample_working.csv")


def test_fake_sheet_client_reads_rows_with_sheet_row_numbers() -> None:
    client = FakeSheetClient("tests/fixtures/leads_sample.csv")

    rows = client.read_rows()

    assert rows[0].row_number == 2
    assert rows[0].values["lead_id"] == "lead_good_001"


def test_fake_sheet_client_updates_existing_and_new_columns() -> None:
    shutil.copyfile("tests/fixtures/leads_sample.csv", WORKING_FIXTURE)

    try:
        client = FakeSheetClient(WORKING_FIXTURE)

        client.update_row(
            2,
            {
                "status": "processing",
                "run_id": "run_123",
                "fit_score": 82,
                "agent_note": "Marked by fake client test.",
            },
        )

        with WORKING_FIXTURE.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))

        assert rows[0]["status"] == "processing"
        assert rows[0]["run_id"] == "run_123"
        assert rows[0]["fit_score"] == "82"
        assert rows[0]["agent_note"] == "Marked by fake client test."
    finally:
        if WORKING_FIXTURE.exists():
            WORKING_FIXTURE.unlink()
