import uuid
from datetime import UTC, datetime

from app.domain.candidates import (
    ImportBatch,
    ImportBatchStatus,
    SourceCandidate,
    SourceProvider,
)
from app.integrations.imports.base import CsvMapper, GenericCsvMapper
from app.integrations.sheets.base import SheetClient
from app.integrations.sheets.constants import (
    IMPORTS_HEADERS,
    IMPORTS_TAB,
    SOURCE_CANDIDATES_HEADERS,
    SOURCE_CANDIDATES_TAB,
)
from app.services.dedupe_service import DedupeService
from app.services.promotion_service import PromotionService


class SheetTabImportService:
    """Import candidates from a Google Sheet tab (user-pasted CSV data)."""

    def __init__(
        self,
        sheet_client: SheetClient,
        mapper: CsvMapper | None = None,
    ) -> None:
        self.sheet_client = sheet_client
        self.mapper = mapper or GenericCsvMapper()

    def import_from_tab(
        self,
        *,
        temp_tab_name: str,
        source_provider: SourceProvider,
        created_by: str | None = None,
        promote_to_leads: bool = False,
    ) -> ImportBatch:
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        batch = ImportBatch(
            import_batch_id=batch_id,
            source_provider=source_provider,
            file_name=temp_tab_name,
            created_by=created_by,
            created_at=datetime.now(UTC).isoformat(),
        )

        rows = self.sheet_client.read_rows(tab_name=temp_tab_name)
        if not rows:
            batch.status = ImportBatchStatus.FAILED
            batch.notes = f"No data found in tab: {temp_tab_name}"
            self._write_batch(batch)
            return batch

        # Convert rows to CSV DictReader-like dicts
        row_dicts = []
        for row in rows:
            values = dict(row.values)
            # Skip empty rows
            if not any(v for v in values.values() if v):
                continue
            row_dicts.append(values)

        if not row_dicts:
            batch.status = ImportBatchStatus.FAILED
            batch.notes = f"No data rows found in tab: {temp_tab_name}"
            self._write_batch(batch)
            return batch

        existing_candidates = self._load_existing_candidates()
        dedupe_service = DedupeService(existing_candidates)
        promotion_service = PromotionService(self.sheet_client) if promote_to_leads else None

        candidates: list[SourceCandidate] = []
        errors: list[str] = []

        for row in row_dicts:
            try:
                mapped = self.mapper.map_row(dict(row))
                mapped["import_batch_id"] = batch_id
                candidate = SourceCandidate.from_mapping(mapped)

                duplicate = dedupe_service.find_duplicate(candidate)
                if duplicate:
                    dedupe_service.mark_duplicate(candidate, duplicate)
                    batch.duplicate_count += 1
                else:
                    candidate.dedupe_key = dedupe_service.generate_dedupe_key(
                        candidate
                    )
                    batch.imported_count += 1

                candidates.append(candidate)
            except Exception as exc:
                batch.error_count += 1
                errors.append(str(exc))

        if promotion_service:
            promoted, rejected = promotion_service.evaluate_and_promote(candidates)
            batch.imported_count -= rejected
            batch.rejected_count += rejected

        batch.total_rows = (
            batch.imported_count
            + batch.error_count
            + batch.duplicate_count
            + batch.rejected_count
        )

        if batch.error_count > 0:
            batch.status = ImportBatchStatus.COMPLETED_WITH_ERRORS
            batch.notes = "; ".join(errors[:10])
        else:
            batch.status = ImportBatchStatus.COMPLETED

        self._write_batch(batch)
        self._write_candidates(candidates)

        return batch

    def _load_existing_candidates(self) -> list[SourceCandidate]:
        import json

        rows = self.sheet_client.read_rows(tab_name=SOURCE_CANDIDATES_TAB)
        candidates = []
        for row in rows:
            values = dict(row.values)
            if not values.get("candidate_id"):
                continue
            raw_data = values.get("raw_data_json")
            if isinstance(raw_data, str) and raw_data:
                try:
                    values["raw_data_json"] = json.loads(raw_data)
                except json.JSONDecodeError:
                    values["raw_data_json"] = None
            try:
                candidates.append(SourceCandidate.model_validate(values))
            except Exception:
                continue
        return candidates

    def _write_batch(self, batch: ImportBatch) -> None:
        self.sheet_client.append_row(
            tab_name=IMPORTS_TAB,
            values=batch.model_dump(mode="json"),
            headers=IMPORTS_HEADERS,
        )

    def _write_candidates(self, candidates: list[SourceCandidate]) -> None:
        for candidate in candidates:
            self.sheet_client.append_row(
                tab_name=SOURCE_CANDIDATES_TAB,
                values=candidate.model_dump(mode="json"),
                headers=SOURCE_CANDIDATES_HEADERS,
            )
