from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict


class SheetRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    row_number: int
    values: dict[str, Any]


class SheetClient(Protocol):
    def read_rows(self, tab_name: str | None = None) -> list[SheetRow]:
        """Return sheet rows with 1-based spreadsheet row numbers."""

    def update_row(
        self,
        row_number: int,
        values: dict[str, Any],
        tab_name: str | None = None,
    ) -> None:
        """Patch values into one row, preserving unspecified columns."""

    def append_row(
        self,
        *,
        tab_name: str,
        values: dict[str, Any],
        headers: list[str],
    ) -> None:
        """Append a row to a specific tab, creating headers if needed."""


def serialize_sheet_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        import json

        return json.dumps(value, ensure_ascii=False)
    return str(value)
