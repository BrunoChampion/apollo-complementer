from fastapi import APIRouter, Depends, HTTPException
from googleapiclient.errors import HttpError
from pydantic import BaseModel, ConfigDict

from app.core.security import verify_apps_script_secret
from app.domain.candidates import SourceProvider
from app.integrations.imports import mapper_for_provider
from app.integrations.sheets.factory import build_sheet_client
from app.services.sheet_tab_import_service import SheetTabImportService

router = APIRouter(prefix="/imports", tags=["imports"])


class ImportFromSheetTabRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_provider: str = "generic"
    temp_tab_name: str = "CSV Import Temp"
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


@router.post("/from_sheet_tab", response_model=ImportBatchResponse)
def import_from_sheet_tab(
    request: ImportFromSheetTabRequest,
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
        sheet_id=request.sheet_id,
        tab_name=request.tab_name,
    )

    service = SheetTabImportService(
        sheet_client=sheet_client,
        mapper=mapper_for_provider(provider),
    )
    try:
        batch = service.import_from_tab(
            temp_tab_name=request.temp_tab_name,
            source_provider=provider,
            created_by=request.created_by,
            promote_to_leads=request.promote_to_leads,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HttpError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ImportBatchResponse.model_validate(batch.model_dump(mode="json"))
