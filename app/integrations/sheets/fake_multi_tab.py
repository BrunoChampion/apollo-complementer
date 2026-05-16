import csv
from pathlib import Path
from typing import Any

from app.integrations.sheets.base import SheetRow, serialize_sheet_value


class MultiTabFakeSheetClient:
    """Fake sheet client that stores each tab as a separate CSV in a directory."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._active_tab: str | None = None

    def _csv_path(self, tab_name: str) -> Path:
        return self.directory / f"{tab_name}.csv"

    def set_active_tab(self, tab_name: str) -> None:
        self._active_tab = tab_name

    def read_rows(self, tab_name: str | None = None) -> list[SheetRow]:
        target = tab_name or self._active_tab
        if not target:
            raise ValueError(
                "tab_name must be provided or set_active_tab must be called"
            )
        csv_path = self._csv_path(target)
        if not csv_path.exists():
            return []
        with csv_path.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            return [
                SheetRow(row_number=index, values=dict(row))
                for index, row in enumerate(reader, start=2)
            ]

    def update_row(
        self,
        row_number: int,
        values: dict[str, Any],
        tab_name: str | None = None,
    ) -> None:
        target = tab_name or self._active_tab
        if not target:
            raise ValueError(
                "tab_name must be provided or set_active_tab must be called"
            )
        rows, fieldnames = self._read_raw_rows(target)
        row_index = row_number - 2
        if row_index < 0 or row_index >= len(rows):
            raise IndexError(f"Row number does not exist: {row_number}")
        for column in values:
            if column not in fieldnames:
                fieldnames.append(column)
        rows[row_index].update(
            {key: serialize_sheet_value(value) for key, value in values.items()}
        )
        self._write_raw_rows(target, rows, fieldnames)

    def append_row(self, *, tab_name: str, values: dict[str, Any], headers: list[str]) -> None:
        csv_path = self._csv_path(tab_name)
        if csv_path.exists():
            rows, fieldnames = self._read_raw_rows(tab_name)
        else:
            rows, fieldnames = [], []
        for column in headers:
            if column not in fieldnames:
                fieldnames.append(column)
        new_row = {header: serialize_sheet_value(values.get(header)) for header in fieldnames}
        rows.append(new_row)
        self._write_raw_rows(tab_name, rows, fieldnames)

    def _read_raw_rows(self, tab_name: str) -> tuple[list[dict[str, str]], list[str]]:
        csv_path = self._csv_path(tab_name)
        with csv_path.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            return list(reader), list(reader.fieldnames or [])

    def _write_raw_rows(
        self,
        tab_name: str,
        rows: list[dict[str, str]],
        fieldnames: list[str],
    ) -> None:
        csv_path = self._csv_path(tab_name)
        with csv_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(
                file, fieldnames=fieldnames, extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(rows)
