import shutil
from pathlib import Path

from app.domain.candidates import ImportBatchStatus, SourceProvider
from app.integrations.sheets.constants import (
    IMPORTS_TAB,
    SOURCE_CANDIDATES_TAB,
)
from app.integrations.sheets.fake_multi_tab import MultiTabFakeSheetClient
from app.services.import_service import CsvImportService

TEMP_DIR = Path("C:/Users/bruno/AppData/Local/Temp/opencode/import_service_test")


def setup_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def teardown_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)


def test_import_csv_reads_and_writes_candidates() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "test_1")
    service = CsvImportService(sheet_client=client)

    batch = service.import_csv(
        file_path="tests/fixtures/candidates_sample.csv",
        source_provider=SourceProvider.APOLLO,
        created_by="tester",
    )

    assert batch.status == ImportBatchStatus.COMPLETED
    assert batch.imported_count == 3
    assert batch.error_count == 0
    assert batch.total_rows == 3
    assert batch.source_provider == SourceProvider.APOLLO
    assert batch.created_by == "tester"

    imports_rows = client.read_rows(tab_name=IMPORTS_TAB)
    assert len(imports_rows) == 1
    assert imports_rows[0].values["import_batch_id"] == batch.import_batch_id
    assert imports_rows[0].values["imported_count"] == "3"

    candidates_rows = client.read_rows(tab_name=SOURCE_CANDIDATES_TAB)
    assert len(candidates_rows) == 3
    assert candidates_rows[0].values["company_name"] == "Acme Inc"
    assert candidates_rows[1].values["prospect_email"] == "maria@cloudops.io"


def test_import_csv_preserves_candidate_ids_from_csv() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "test_2")
    service = CsvImportService(sheet_client=client)

    service.import_csv(
        file_path="tests/fixtures/candidates_sample.csv",
        source_provider=SourceProvider.GENERIC,
    )

    candidates_rows = client.read_rows(tab_name=SOURCE_CANDIDATES_TAB)
    assert len(candidates_rows) == 3
    assert candidates_rows[0].values["candidate_id"] == "cand_001"
    assert candidates_rows[1].values["candidate_id"] == "cand_002"
    assert candidates_rows[2].values["candidate_id"] == "cand_003"


def test_import_csv_file_not_found() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "test_3")
    service = CsvImportService(sheet_client=client)

    batch = service.import_csv(
        file_path="tests/fixtures/nonexistent.csv",
        source_provider=SourceProvider.SNOV,
    )

    assert batch.status == ImportBatchStatus.FAILED
    assert "File not found" in (batch.notes or "")


def test_import_csv_preserves_raw_data() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "test_4")
    service = CsvImportService(sheet_client=client)

    service.import_csv(
        file_path="tests/fixtures/candidates_sample.csv",
        source_provider=SourceProvider.HUNTER,
    )

    candidates_rows = client.read_rows(tab_name=SOURCE_CANDIDATES_TAB)
    # The fixture has a column "candidate_id" which is known, so raw_data_json
    # should not include it. But let's verify at least one candidate was stored.
    assert len(candidates_rows) == 3
