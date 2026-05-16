from typing import Any

import pytest

from app.integrations.sheets.google import GoogleSheetClient


class FakeExecute:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result

    def execute(self) -> dict[str, Any]:
        return self.result


class FakeValuesResource:
    def __init__(self) -> None:
        self.batch_update_body: dict[str, Any] | None = None
        self.update_body: dict[str, Any] | None = None
        self.append_body: dict[str, Any] | None = None

    def get(self, *, spreadsheetId: str, range: str):
        assert spreadsheetId == "sheet_123"
        assert range in {"Leads!A1:ZZ", "Leads!1:1", "Runs!1:1"}
        if range == "Runs!1:1":
            return FakeExecute({"values": []})
        return FakeExecute(
            {
                "values": [
                    ["lead_id", "company_name", "status", "run_id"],
                    ["lead_001", "Andes ERP Partners", "new", ""],
                ]
            }
        )

    def batchUpdate(self, *, spreadsheetId: str, body: dict[str, Any]):
        assert spreadsheetId == "sheet_123"
        self.batch_update_body = body
        return FakeExecute({})

    def update(
        self,
        *,
        spreadsheetId: str,
        range: str,
        valueInputOption: str,
        body: dict[str, Any],
    ):
        assert spreadsheetId == "sheet_123"
        assert range == "Runs!1:1"
        assert valueInputOption == "USER_ENTERED"
        self.update_body = body
        return FakeExecute({})

    def append(
        self,
        *,
        spreadsheetId: str,
        range: str,
        valueInputOption: str,
        insertDataOption: str,
        body: dict[str, Any],
    ):
        assert spreadsheetId == "sheet_123"
        assert range == "Runs!A:ZZ"
        assert valueInputOption == "USER_ENTERED"
        assert insertDataOption == "INSERT_ROWS"
        self.append_body = body
        return FakeExecute({})


class FakeSpreadsheetsResource:
    def __init__(self, values_resource: FakeValuesResource) -> None:
        self.values_resource = values_resource
        self.batch_update_body: dict[str, Any] | None = None

    def values(self) -> FakeValuesResource:
        return self.values_resource

    def get(self, *, spreadsheetId: str):
        assert spreadsheetId == "sheet_123"
        return FakeExecute({"sheets": [{"properties": {"title": "Leads"}}]})

    def batchUpdate(self, *, spreadsheetId: str, body: dict[str, Any]):
        assert spreadsheetId == "sheet_123"
        self.batch_update_body = body
        return FakeExecute({})


class FakeSheetsService:
    def __init__(self) -> None:
        self.values_resource = FakeValuesResource()
        self.spreadsheets_resource = FakeSpreadsheetsResource(self.values_resource)

    def spreadsheets(self) -> FakeSpreadsheetsResource:
        return self.spreadsheets_resource


def test_google_sheet_client_reads_rows_and_preserves_row_numbers() -> None:
    service = FakeSheetsService()
    client = GoogleSheetClient(spreadsheet_id="sheet_123", tab_name="Leads", service=service)

    rows = client.read_rows()

    assert len(rows) == 1
    assert rows[0].row_number == 2
    assert rows[0].values["lead_id"] == "lead_001"


def test_google_sheet_client_updates_known_columns() -> None:
    service = FakeSheetsService()
    client = GoogleSheetClient(spreadsheet_id="sheet_123", tab_name="Leads", service=service)
    client.read_rows()

    client.update_row(2, {"status": "processing", "run_id": "run_123"})

    assert service.values_resource.batch_update_body == {
        "valueInputOption": "USER_ENTERED",
        "data": [
            {"range": "Leads!C2", "values": [["processing"]]},
            {"range": "Leads!D2", "values": [["run_123"]]},
        ],
    }


def test_google_sheet_client_rejects_unknown_columns() -> None:
    service = FakeSheetsService()
    client = GoogleSheetClient(spreadsheet_id="sheet_123", tab_name="Leads", service=service)
    client.read_rows()

    with pytest.raises(ValueError, match="Column does not exist"):
        client.update_row(2, {"missing_column": "value"})


def test_google_sheet_client_appends_rows_to_activity_tab() -> None:
    service = FakeSheetsService()
    client = GoogleSheetClient(spreadsheet_id="sheet_123", tab_name="Leads", service=service)

    client.append_row(
        tab_name="Runs",
        headers=["run_id", "status"],
        values={"run_id": "run_123", "status": "completed"},
    )

    assert service.spreadsheets_resource.batch_update_body == {
        "requests": [{"addSheet": {"properties": {"title": "Runs"}}}]
    }
    assert service.values_resource.update_body == {"values": [["run_id", "status"]]}
    assert service.values_resource.append_body == {"values": [["run_123", "completed"]]}
