from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.integrations.sheets.base import SheetRow, serialize_sheet_value

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


class GoogleSheetClient:
    def __init__(
        self,
        *,
        spreadsheet_id: str,
        tab_name: str = "Leads",
        credentials_path: str | None = None,
        service: Any | None = None,
    ) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.tab_name = tab_name
        self._service = service
        self.credentials_path = credentials_path
        self._headers: list[str] | None = None
        self._headers_by_tab: dict[str, list[str]] = {}

    def read_rows(self, tab_name: str | None = None) -> list[SheetRow]:
        target = tab_name or self.tab_name
        try:
            values = (
                self._sheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=_sheet_range(target, "A1:ZZ"))
                .execute()
                .get("values", [])
            )
        except HttpError as exc:
            if exc.resp.status == 400:
                available_tabs = ", ".join(self.list_tab_names())
                raise ValueError(
                    f"Could not read Google Sheet tab '{target}'. "
                    f"Available tabs: {available_tabs}"
                ) from exc
            raise
        if not values:
            if tab_name is None:
                self._headers = []
            return []

        headers = [str(header) for header in values[0]]
        self._headers_by_tab[target] = headers
        if tab_name is None:
            self._headers = headers
        rows: list[SheetRow] = []
        for row_number, row_values in enumerate(values[1:], start=2):
            row = {
                header: row_values[index] if index < len(row_values) else ""
                for index, header in enumerate(headers)
            }
            rows.append(SheetRow(row_number=row_number, values=row))
        return rows

    def update_row(
        self,
        row_number: int,
        values: dict[str, Any],
        tab_name: str | None = None,
    ) -> None:
        target = tab_name or self.tab_name
        headers = self._headers_by_tab.get(target) or self._read_headers(target)
        if not headers:
            raise ValueError("Cannot update a Google Sheet without a header row.")

        data = []
        for key, value in values.items():
            if key not in headers:
                raise ValueError(f"Column does not exist in Google Sheet: {key}")
            column = _column_letter(headers.index(key) + 1)
            data.append(
                {
                    "range": _sheet_range(target, f"{column}{row_number}"),
                    "values": [[serialize_sheet_value(value)]],
                }
            )

        if not data:
            return

        self._sheets().values().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": data},
        ).execute()

    def append_row(self, *, tab_name: str, values: dict[str, Any], headers: list[str]) -> None:
        self._ensure_tab_exists(tab_name)
        final_headers = self._ensure_headers(tab_name, headers)
        row = [serialize_sheet_value(values.get(header)) for header in final_headers]
        self._sheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=_sheet_range(tab_name, "A:ZZ"),
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

    def _read_headers(self, tab_name: str | None = None) -> list[str]:
        target = tab_name or self.tab_name
        values = (
            self._sheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=_sheet_range(target, "1:1"))
            .execute()
            .get("values", [])
        )
        headers = [str(header) for header in values[0]] if values else []
        self._headers_by_tab[target] = headers
        if tab_name is None:
            self._headers = headers
        return headers

    def _ensure_headers(self, tab_name: str, headers: list[str]) -> list[str]:
        values = (
            self._sheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=_sheet_range(tab_name, "1:1"))
            .execute()
            .get("values", [])
        )
        existing_headers = [str(header) for header in values[0]] if values else []
        if existing_headers == headers:
            self._headers_by_tab[tab_name] = existing_headers
            return existing_headers
        if existing_headers:
            missing_headers = [header for header in headers if header not in existing_headers]
            if not missing_headers:
                self._headers_by_tab[tab_name] = existing_headers
                return existing_headers
            headers = existing_headers + missing_headers

        self._sheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=_sheet_range(tab_name, "1:1"),
            valueInputOption="USER_ENTERED",
            body={"values": [headers]},
        ).execute()
        self._headers_by_tab[tab_name] = headers
        return headers

    def _ensure_tab_exists(self, tab_name: str) -> None:
        sheet_titles = set(self.list_tab_names())
        if tab_name in sheet_titles:
            return
        self._sheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
        ).execute()

    def list_tab_names(self) -> list[str]:
        spreadsheet = self._sheets().get(spreadsheetId=self.spreadsheet_id).execute()
        return [
            sheet["properties"]["title"]
            for sheet in spreadsheet.get("sheets", [])
            if "properties" in sheet and "title" in sheet["properties"]
        ]

    def _sheets(self):
        return self._service.spreadsheets()

    @property
    def _service(self):
        if self.__service is None:
            if not self.credentials_path:
                raise ValueError("credentials_path is required when service is not injected.")
            credentials = service_account.Credentials.from_service_account_file(
                Path(self.credentials_path),
                scopes=[SHEETS_SCOPE],
            )
            self.__service = build("sheets", "v4", credentials=credentials)
        return self.__service

    @_service.setter
    def _service(self, value):
        self.__service = value


def _column_letter(column_number: int) -> str:
    letters = ""
    while column_number:
        column_number, remainder = divmod(column_number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _sheet_range(tab_name: str, cell_range: str) -> str:
    escaped = tab_name.replace("'", "''")
    return f"'{escaped}'!{cell_range}"
