from app.core.config import get_settings
from app.integrations.sheets.base import SheetClient
from app.integrations.sheets.fake import FakeSheetClient
from app.integrations.sheets.google import GoogleSheetClient


def build_sheet_client(
    *,
    source: str,
    sheet_path: str | None = None,
    sheet_id: str | None = None,
    tab_name: str | None = None,
) -> SheetClient:
    settings = get_settings()
    if source == "google_sheets":
        if not sheet_id:
            raise ValueError("sheet_id is required for google_sheets source")
        return GoogleSheetClient(
            spreadsheet_id=sheet_id,
            tab_name=tab_name or settings.google_sheets_default_tab,
            credentials_path=settings.google_application_credentials,
        )
    return FakeSheetClient(sheet_path or settings.fake_sheet_path)
