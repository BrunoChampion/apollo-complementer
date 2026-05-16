from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.core.security import verify_apps_script_secret
from app.integrations.sheets.factory import build_sheet_client
from app.services.orchestration_service import OrchestrationService

router = APIRouter(prefix="/orchestrate", tags=["orchestration"])
DBSession = Depends(get_db)


class OrchestrateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_run_id: str | None = None
    candidate_ids: list[str] | None = None
    run_id: str = "manual"
    source: str = "fake_sheet"
    sheet_path: str | None = None


class OrchestrateResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    candidates_processed: int
    promoted: int
    rejected: int
    enrichment_results: int
    drafts_created: int
    job_run_id: str | None
    run_id: str


@router.post("", response_model=OrchestrateResponse)
def orchestrate(
    request: OrchestrateRequest,
    _: None = Depends(verify_apps_script_secret),
    session: Session = DBSession,
) -> OrchestrateResponse:
    settings = get_settings()
    service = OrchestrationService(
        sheet_client=build_sheet_client(
            source=request.source,
            sheet_path=request.sheet_path or settings.fake_sheet_path,
        ),
    )
    try:
        result = service.run_end_to_end(
            job_run_id=request.job_run_id,
            candidate_ids=request.candidate_ids,
            run_id=request.run_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return OrchestrateResponse.model_validate(result)
