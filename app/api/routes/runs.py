from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.core.security import verify_apps_script_secret
from app.db.models import LeadRun, Run
from app.db.repositories import RunRepository
from app.db.session import SessionLocal
from app.services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["runs"])
DBSession = Depends(get_db)


class CreateRunRequest(BaseModel):
    source: str = "fake_sheet"
    sheet_id: str | None = None
    sheet_path: str | None = None
    tab_name: str | None = None
    created_by: str | None = None
    process_async: bool = True


class LeadRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lead_id: str
    row_number: int | None
    action: str
    status: str
    error_message: str | None


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    sheet_id: str | None
    status: str
    total_rows: int
    success_count: int
    error_count: int
    created_by: str | None
    summary: dict[str, Any] | None
    lead_runs: list[LeadRunResponse] = []


class CreateRunResponse(BaseModel):
    run_id: str
    status: str


@router.post("", response_model=CreateRunResponse)
def create_run(
    request: CreateRunRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_apps_script_secret),
    session: Session = DBSession,
) -> CreateRunResponse:
    settings = get_settings()
    service = RunService(RunRepository(session))
    run = service.create_run(
        source=request.source,
        sheet_id=request.sheet_id or request.sheet_path or settings.fake_sheet_path,
        created_by=request.created_by,
    )
    sheet_path = request.sheet_path or settings.fake_sheet_path

    if request.process_async:
        background_tasks.add_task(
            process_run_background,
            run.id,
            request.source,
            sheet_path,
            request.sheet_id,
            request.tab_name,
        )
    else:
        service.process_run(
            run.id,
            sheet_path=sheet_path,
            source=request.source,
            sheet_id=request.sheet_id,
            tab_name=request.tab_name,
        )

    return CreateRunResponse(run_id=run.id, status="queued")


@router.post("/{run_id}/process", response_model=RunResponse)
def process_run(
    run_id: str,
    source: str = "fake_sheet",
    sheet_path: str | None = None,
    sheet_id: str | None = None,
    tab_name: str | None = None,
) -> RunResponse:
    settings = get_settings()
    with SessionLocal() as session:
        service = RunService(RunRepository(session))
        try:
            run = service.process_run(
                run_id,
                sheet_path=sheet_path or settings.fake_sheet_path,
                source=source,
                sheet_id=sheet_id,
                tab_name=tab_name,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return run_to_response(run, service.repository.list_lead_runs(run.id))


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: str, session: Session = DBSession) -> RunResponse:
    repository = RunRepository(session)
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run_to_response(run, repository.list_lead_runs(run.id))


def process_run_background(
    run_id: str,
    source: str,
    sheet_path: str,
    sheet_id: str | None,
    tab_name: str | None,
) -> None:
    with SessionLocal() as session:
        service = RunService(RunRepository(session))
        service.process_run(
            run_id,
            sheet_path=sheet_path,
            source=source,
            sheet_id=sheet_id,
            tab_name=tab_name,
        )


def run_to_response(run: Run, lead_runs: list[LeadRun]) -> RunResponse:
    response = RunResponse.model_validate(run)
    response.lead_runs = [LeadRunResponse.model_validate(lead_run) for lead_run in lead_runs]
    return response
