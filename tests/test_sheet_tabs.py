import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.integrations.sheets.base import serialize_sheet_value
from app.integrations.sheets.constants import (
    ALL_TAB_NAMES,
    EMAIL_DRAFTS_HEADERS,
    EMAIL_DRAFTS_TAB,
    ENRICHMENT_HEADERS,
    ENRICHMENT_TAB,
    IMPORTS_HEADERS,
    IMPORTS_TAB,
    LEADS_HEADERS,
    LEADS_TAB,
    RUNS_HEADERS,
    RUNS_TAB,
    SOURCE_CANDIDATES_HEADERS,
    SOURCE_CANDIDATES_TAB,
    TAB_HEADERS,
)
from app.integrations.sheets.fake_multi_tab import MultiTabFakeSheetClient
from app.integrations.sheets.google import GoogleSheetClient

TEMP_DIR = Path("C:/Users/bruno/AppData/Local/Temp/opencode/sheet_tabs_test")


def setup_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def teardown_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)


def test_all_tabs_defined() -> None:
    assert ALL_TAB_NAMES == [
        LEADS_TAB,
        RUNS_TAB,
        EMAIL_DRAFTS_TAB,
        IMPORTS_TAB,
        SOURCE_CANDIDATES_TAB,
        ENRICHMENT_TAB,
    ]


def test_tab_headers_coverage() -> None:
    for tab in ALL_TAB_NAMES:
        assert tab in TAB_HEADERS
        assert len(TAB_HEADERS[tab]) > 0


def test_leads_headers_expected() -> None:
    assert "lead_id" in LEADS_HEADERS
    assert "company_name" in LEADS_HEADERS
    assert "action" in LEADS_HEADERS
    assert "status" in LEADS_HEADERS
    assert "email_draft" in LEADS_HEADERS
    assert "run_id" in LEADS_HEADERS


def test_source_candidates_headers_expected() -> None:
    assert "candidate_id" in SOURCE_CANDIDATES_HEADERS
    assert "source_provider" in SOURCE_CANDIDATES_HEADERS
    assert "company_domain" in SOURCE_CANDIDATES_HEADERS
    assert "candidate_status" in SOURCE_CANDIDATES_HEADERS
    assert "dedupe_key" in SOURCE_CANDIDATES_HEADERS
    assert "import_batch_id" in SOURCE_CANDIDATES_HEADERS


def test_imports_headers_expected() -> None:
    assert "import_batch_id" in IMPORTS_HEADERS
    assert "source_provider" in IMPORTS_HEADERS
    assert "total_rows" in IMPORTS_HEADERS
    assert "duplicate_count" in IMPORTS_HEADERS
    assert "status" in IMPORTS_HEADERS


def test_enrichment_headers_expected() -> None:
    assert "enrichment_id" in ENRICHMENT_HEADERS
    assert "company_summary" in ENRICHMENT_HEADERS
    assert "operational_pain_hypothesis" in ENRICHMENT_HEADERS
    assert "confidence_score" in ENRICHMENT_HEADERS
    assert "evidence_count" in ENRICHMENT_HEADERS
    assert "recommended_action" in ENRICHMENT_HEADERS


def test_runs_headers_expected() -> None:
    assert "run_id" in RUNS_HEADERS
    assert "success_count" in RUNS_HEADERS
    assert "drafts_created" in RUNS_HEADERS


def test_email_drafts_headers_expected() -> None:
    assert "email_draft" in EMAIL_DRAFTS_HEADERS
    assert "draft_status" in EMAIL_DRAFTS_HEADERS
    assert "quality_score" in EMAIL_DRAFTS_HEADERS
    assert "gmail_draft_id" in EMAIL_DRAFTS_HEADERS
    assert "sent_manually" in EMAIL_DRAFTS_HEADERS
    assert "reply_status" in EMAIL_DRAFTS_HEADERS


class TestMultiTabFakeSheetClient:
    def test_reads_and_appends_to_multiple_tabs(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "multi_tab_1")

        client.append_row(
            tab_name=IMPORTS_TAB,
            values={
                "import_batch_id": "batch_001",
                "source_provider": "apollo",
                "total_rows": 50,
            },
            headers=IMPORTS_HEADERS,
        )
        client.append_row(
            tab_name=SOURCE_CANDIDATES_TAB,
            values={
                "candidate_id": "cand_001",
                "source_provider": "apollo",
                "company_name": "Acme",
            },
            headers=SOURCE_CANDIDATES_HEADERS,
        )

        imports_rows = client.read_rows(tab_name=IMPORTS_TAB)
        assert len(imports_rows) == 1
        assert imports_rows[0].values["import_batch_id"] == "batch_001"

        candidates_rows = client.read_rows(tab_name=SOURCE_CANDIDATES_TAB)
        assert len(candidates_rows) == 1
        assert candidates_rows[0].values["candidate_id"] == "cand_001"

    def test_update_row_in_specific_tab(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "multi_tab_2")
        client.append_row(
            tab_name=ENRICHMENT_TAB,
            values={"enrichment_id": "enrich_001", "confidence_score": "70"},
            headers=ENRICHMENT_HEADERS,
        )
        client.update_row(
            row_number=2,
            values={"confidence_score": "85"},
            tab_name=ENRICHMENT_TAB,
        )
        rows = client.read_rows(tab_name=ENRICHMENT_TAB)
        assert rows[0].values["confidence_score"] == "85"

    def test_empty_tab_returns_empty_list(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "multi_tab_3")
        assert client.read_rows(tab_name=LEADS_TAB) == []


class TestGoogleSheetClientAppendRow:
    @patch("app.integrations.sheets.google.build")
    def test_appends_to_imports_tab(self, mock_build: MagicMock) -> None:
        mock_service = MagicMock()
        mock_sheets = MagicMock()
        mock_service.spreadsheets.return_value = mock_sheets
        mock_build.return_value = mock_service

        mock_sheets.get.return_value.execute.return_value = {"sheets": []}
        mock_sheets.batchUpdate.return_value.execute.return_value = {}
        mock_sheets.values.return_value.get.return_value.execute.return_value = {
            "values": []
        }
        mock_sheets.values.return_value.update.return_value.execute.return_value = {}
        mock_sheets.values.return_value.append.return_value.execute.return_value = {}

        client = GoogleSheetClient(
            spreadsheet_id="test_spreadsheet_id",
            tab_name=LEADS_TAB,
            service=mock_service,
        )

        client.append_row(
            tab_name=IMPORTS_TAB,
            values={
                "import_batch_id": "batch_001",
                "source_provider": "apollo",
                "status": "running",
            },
            headers=IMPORTS_HEADERS,
        )

        mock_sheets.batchUpdate.assert_called_once()
        call_body = mock_sheets.batchUpdate.call_args[1]["body"]
        assert (
            call_body["requests"][0]["addSheet"]["properties"]["title"]
            == IMPORTS_TAB
        )

        mock_sheets.values.return_value.update.assert_called_once()
        update_call = mock_sheets.values.return_value.update.call_args
        assert update_call[1]["range"] == f"'{IMPORTS_TAB}'!1:1"

        mock_sheets.values.return_value.append.assert_called_once()
        append_call = mock_sheets.values.return_value.append.call_args
        assert append_call[1]["range"] == f"'{IMPORTS_TAB}'!A:ZZ"
        appended_values = append_call[1]["body"]["values"][0]
        assert appended_values[IMPORTS_HEADERS.index("import_batch_id")] == "batch_001"
        assert appended_values[IMPORTS_HEADERS.index("source_provider")] == "apollo"
        assert appended_values[IMPORTS_HEADERS.index("status")] == "running"

    @patch("app.integrations.sheets.google.build")
    def test_appends_to_source_candidates_tab(
        self, mock_build: MagicMock
    ) -> None:
        mock_service = MagicMock()
        mock_sheets = MagicMock()
        mock_service.spreadsheets.return_value = mock_sheets
        mock_build.return_value = mock_service

        mock_sheets.get.return_value.execute.return_value = {"sheets": []}
        mock_sheets.batchUpdate.return_value.execute.return_value = {}
        mock_sheets.values.return_value.get.return_value.execute.return_value = {
            "values": []
        }
        mock_sheets.values.return_value.update.return_value.execute.return_value = {}
        mock_sheets.values.return_value.append.return_value.execute.return_value = {}

        client = GoogleSheetClient(
            spreadsheet_id="test_spreadsheet_id",
            tab_name=LEADS_TAB,
            service=mock_service,
        )

        client.append_row(
            tab_name=SOURCE_CANDIDATES_TAB,
            values={
                "candidate_id": "cand_002",
                "company_name": "CloudOps",
                "candidate_status": "new",
                "prospect_email": "juan@cloudops.io",
            },
            headers=SOURCE_CANDIDATES_HEADERS,
        )

        mock_sheets.values.return_value.append.assert_called_once()
        append_call = mock_sheets.values.return_value.append.call_args
        appended_values = append_call[1]["body"]["values"][0]
        assert (
            appended_values[SOURCE_CANDIDATES_HEADERS.index("candidate_id")]
            == "cand_002"
        )
        assert (
            appended_values[SOURCE_CANDIDATES_HEADERS.index("prospect_email")]
            == "juan@cloudops.io"
        )

    @patch("app.integrations.sheets.google.build")
    def test_append_row_uses_existing_header_order_when_adding_new_columns(
        self, mock_build: MagicMock
    ) -> None:
        mock_service = MagicMock()
        mock_sheets = MagicMock()
        mock_service.spreadsheets.return_value = mock_sheets
        mock_build.return_value = mock_service

        existing_headers = [
            "lead_id",
            "company_name",
            "company_website",
            "prospect_name",
            "prospect_title",
        ]
        mock_sheets.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"title": LEADS_TAB}}]
        }
        mock_sheets.values.return_value.get.return_value.execute.return_value = {
            "values": [existing_headers]
        }
        mock_sheets.values.return_value.update.return_value.execute.return_value = {}
        mock_sheets.values.return_value.append.return_value.execute.return_value = {}

        client = GoogleSheetClient(
            spreadsheet_id="test_spreadsheet_id",
            tab_name=LEADS_TAB,
            service=mock_service,
        )

        client.append_row(
            tab_name=LEADS_TAB,
            values={
                "lead_id": "lead_1",
                "company_name": "Acme",
                "company_website": "https://acme.com",
                "company_domain": "acme.com",
                "company_linkedin_url": "https://linkedin.com/company/acme",
                "prospect_name": "Ana",
                "prospect_title": "COO",
            },
            headers=LEADS_HEADERS,
        )

        appended = mock_sheets.values.return_value.append.call_args[1]["body"]["values"][0]
        final_headers = existing_headers + [
            header for header in LEADS_HEADERS if header not in existing_headers
        ]
        assert appended[final_headers.index("prospect_name")] == "Ana"
        assert appended[final_headers.index("company_domain")] == "acme.com"


class TestSerializeSheetValue:
    def test_none_returns_empty_string(self) -> None:
        assert serialize_sheet_value(None) == ""

    def test_bool_serializes_to_lowercase(self) -> None:
        assert serialize_sheet_value(True) == "true"
        assert serialize_sheet_value(False) == "false"

    def test_list_serializes_to_json(self) -> None:
        assert serialize_sheet_value(["a", "b"]) == '["a", "b"]'

    def test_dict_serializes_to_json(self) -> None:
        assert serialize_sheet_value({"key": "value"}) == '{"key": "value"}'

    def test_int_serializes_to_string(self) -> None:
        assert serialize_sheet_value(42) == "42"
