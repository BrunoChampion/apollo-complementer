from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.config import get_settings
from app.integrations.sheets.factory import build_sheet_client
from app.services.export_service import export_approved_leads_csv

router = APIRouter(prefix="/exports", tags=["exports"])


class ExportRequest(BaseModel):
    source: str = "fake_sheet"
    sheet_path: str | None = None
    sheet_id: str | None = None
    tab_name: str | None = None


@router.post("/smartlead-csv")
def export_smartlead_csv(request: ExportRequest) -> Response:
    return _export_csv(request, platform="smartlead", filename="smartlead_export.csv")


@router.post("/instantly-csv")
def export_instantly_csv(request: ExportRequest) -> Response:
    return _export_csv(request, platform="instantly", filename="instantly_export.csv")


def _export_csv(request: ExportRequest, *, platform: str, filename: str) -> Response:
    settings = get_settings()
    sheet_client = build_sheet_client(
        source=request.source,
        sheet_path=request.sheet_path or settings.fake_sheet_path,
        sheet_id=request.sheet_id,
        tab_name=request.tab_name,
    )
    content = export_approved_leads_csv(sheet_client, platform=platform)  # type: ignore[arg-type]
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
