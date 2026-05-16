import csv
from io import StringIO

from app.integrations.sheets.fake import FakeSheetClient
from app.services.export_service import EXPORT_COLUMNS, export_approved_leads_csv, split_name


def test_exports_only_approved_or_export_ready_leads() -> None:
    content = export_approved_leads_csv(
        FakeSheetClient("tests/fixtures/leads_export.csv"),
        platform="smartlead",
    )

    rows = list(csv.DictReader(StringIO(content)))

    assert rows[0].keys() == set(EXPORT_COLUMNS)
    assert len(rows) == 2
    assert rows[0]["email"] == "camila@andeserp.example.com"
    assert rows[0]["first_name"] == "Camila"
    assert rows[0]["last_name"] == "Rojas"
    assert rows[0]["email_subject"] == "Asunto final"
    assert rows[0]["email_body"] == "Mensaje final"
    assert rows[1]["email_body"] == "Revised cyber"


def test_instantly_export_uses_same_safe_csv_contract() -> None:
    content = export_approved_leads_csv(
        FakeSheetClient("tests/fixtures/leads_export.csv"),
        platform="instantly",
    )

    assert content.startswith(",".join(EXPORT_COLUMNS))
    assert "localshop" not in content


def test_split_name_handles_empty_and_single_names() -> None:
    assert split_name(None) == ("", "")
    assert split_name("Camila") == ("Camila", "")
    assert split_name("Camila Rojas Vega") == ("Camila", "Rojas Vega")
