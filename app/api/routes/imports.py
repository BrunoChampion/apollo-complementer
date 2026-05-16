from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.core.security import verify_apps_script_secret
from app.domain.candidates import SourceProvider
from app.integrations.imports import mapper_for_provider
from app.integrations.sheets.factory import build_sheet_client
from app.services.import_service import CsvImportService

router = APIRouter(prefix="/imports", tags=["imports"])


class ImportCsvRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_provider: str = "generic"
    file_path: str
    source: str = "fake_sheet"
    sheet_id: str | None = None
    tab_name: str | None = None
    created_by: str | None = None
    promote_to_leads: bool = False


class ImportBatchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    import_batch_id: str
    source_provider: str
    source_type: str
    file_name: str | None
    created_by: str | None
    created_at: str | None
    total_rows: int
    imported_count: int
    duplicate_count: int
    rejected_count: int
    error_count: int
    status: str
    notes: str | None


@router.post("/csv", response_model=ImportBatchResponse)
def import_csv(
    request: ImportCsvRequest,
    _: None = Depends(verify_apps_script_secret),
) -> ImportBatchResponse:
    try:
        provider = SourceProvider(request.source_provider)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_provider: {request.source_provider}",
        ) from exc

    sheet_client = build_sheet_client(
        source=request.source,
        sheet_path=request.file_path,
        sheet_id=request.sheet_id,
        tab_name=request.tab_name,
    )

    service = CsvImportService(
        sheet_client=sheet_client,
        mapper=mapper_for_provider(provider),
    )
    batch = service.import_csv(
        file_path=request.file_path,
        source_provider=provider,
        created_by=request.created_by,
        promote_to_leads=request.promote_to_leads,
    )

    return ImportBatchResponse.model_validate(batch.model_dump(mode="json"))
