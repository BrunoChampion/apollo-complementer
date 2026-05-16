import csv
from pathlib import Path
from typing import Any

from app.integrations.sheets.base import SheetRow, serialize_sheet_value


class FakeSheetClient:
    def __init__(self, csv_path: str | Path) -> None:
        self.csv_path = Path(csv_path)

    def read_rows(self, tab_name: str | None = None) -> list[SheetRow]:
        with self.csv_path.open(encoding="utf-8", newline="") as file:
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
        rows, fieldnames = self._read_raw_rows()
        row_index = row_number - 2

        if row_index < 0 or row_index >= len(rows):
            raise IndexError(f"Row number does not exist: {row_number}")

        for column in values:
            if column not in fieldnames:
                fieldnames.append(column)

        rows[row_index].update(
            {key: serialize_sheet_value(value) for key, value in values.items()}
        )
        self._write_raw_rows(rows, fieldnames)

    def _read_raw_rows(self) -> tuple[list[dict[str, str]], list[str]]:
        with self.csv_path.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            return list(reader), list(reader.fieldnames or [])

    def append_row(self, *, tab_name: str, values: dict[str, Any], headers: list[str]) -> None:
        rows, fieldnames = self._read_raw_rows()
        for column in headers:
            if column not in fieldnames:
                fieldnames.append(column)
        new_row = {header: serialize_sheet_value(values.get(header)) for header in fieldnames}
        rows.append(new_row)
        self._write_raw_rows(rows, fieldnames)

    def _write_raw_rows(self, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
        with self.csv_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
