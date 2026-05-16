import csv

from app.domain.candidates import SourceProvider
from app.integrations.imports import mapper_for_provider
from app.integrations.sheets.constants import SOURCE_CANDIDATES_TAB
from app.integrations.sheets.fake_multi_tab import MultiTabFakeSheetClient
from app.services.sheet_tab_import_service import SheetTabImportService


def test_import_from_apollo_sheet_tab_uses_provider_mapper(tmp_path) -> None:
    client = MultiTabFakeSheetClient(tmp_path)
    temp_tab = "CSV Import Temp"
    with (tmp_path / f"{temp_tab}.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "First Name",
                "Last Name",
                "Title",
                "Company Name",
                "Website",
                "Country",
                "Apollo Contact Id",
                "Secondary Email",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "First Name": "Alejandra",
                "Last Name": "Mardones",
                "Title": "COO",
                "Company Name": "Teamcore",
                "Website": "https://teamcore.com",
                "Country": "Chile",
                "Apollo Contact Id": "apollo-1",
                "Secondary Email": "alejandra.personal@example.com",
            }
        )

    service = SheetTabImportService(
        sheet_client=client,
        mapper=mapper_for_provider(SourceProvider.APOLLO),
    )

    batch = service.import_from_tab(
        temp_tab_name=temp_tab,
        source_provider=SourceProvider.APOLLO,
    )

    rows = client.read_rows(tab_name=SOURCE_CANDIDATES_TAB)
    assert batch.imported_count == 1
    assert batch.error_count == 0
    assert len(rows) == 1
    assert rows[0].values["company_name"] == "Teamcore"
    assert rows[0].values["prospect_email"] == ""
    assert "alejandra.personal@example.com" in rows[0].values["raw_data_json"]
