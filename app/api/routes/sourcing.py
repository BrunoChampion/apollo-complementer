from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.core.security import verify_apps_script_secret
from app.db.repositories import ProviderUsageRepository, SourcingJobRepository
from app.integrations.apollo.factory import build_apollo_client
from app.integrations.sheets.factory import build_sheet_client
from app.services.credit_budget_service import CreditBudgetService
from app.services.sourcing_job_service import SourcingJobService

router = APIRouter(prefix="/sourcing/jobs", tags=["sourcing"])
DBSession = Depends(get_db)


class CreateSourcingJobRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    description: str | None = None
    provider: str = "apollo"
    query_params: dict[str, Any] | None = None
    max_candidates: int = 50
    enrich_emails: bool = False
    created_by: str | None = None


class UpdateSourcingJobRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    description: str | None = None
    query_params: dict[str, Any] | None = None
    max_candidates: int | None = None
    enrich_emails: bool | None = None
    is_active: bool | None = None


class SourcingJobResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: str
    name: str
    description: str | None
    provider: str
    query_params: dict | None
    max_candidates: int
    enrich_emails: bool
    is_active: bool
    created_by: str | None
    created_at: datetime | None
    updated_at: datetime | None


class RunJobResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_id: str
    job_run_id: str
    status: str
    total_found: int
    imported: int
    duplicated: int
    rejected: int
    emails_enriched: int
    apollo_enrichment_credits_used: int = 0


def _build_service(session: Session) -> SourcingJobService:
    settings = get_settings()
    return SourcingJobService(
        repository=SourcingJobRepository(session),
        apollo_client=build_apollo_client(settings),
        sheet_client=build_sheet_client(
            source=settings.fake_sheet_path,
        ),
        credit_budget_service=CreditBudgetService(
            repository=ProviderUsageRepository(session),
            settings=settings,
        ),
    )


@router.post("", response_model=SourcingJobResponse)
def create_job(
    request: CreateSourcingJobRequest,
    _: None = Depends(verify_apps_script_secret),
    session: Session = DBSession,
) -> SourcingJobResponse:
    service = _build_service(session)
    job = service.create_job(**request.model_dump())
    return SourcingJobResponse.model_validate(job)


@router.get("", response_model=list[SourcingJobResponse])
def list_jobs(
    _: None = Depends(verify_apps_script_secret),
    session: Session = DBSession,
) -> list[SourcingJobResponse]:
    service = _build_service(session)
    jobs = service.list_jobs()
    return [SourcingJobResponse.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=SourcingJobResponse)
def get_job(
    job_id: str,
    _: None = Depends(verify_apps_script_secret),
    session: Session = DBSession,
) -> SourcingJobResponse:
    service = _build_service(session)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return SourcingJobResponse.model_validate(job)


@router.patch("/{job_id}", response_model=SourcingJobResponse)
def update_job(
    job_id: str,
    request: UpdateSourcingJobRequest,
    _: None = Depends(verify_apps_script_secret),
    session: Session = DBSession,
) -> SourcingJobResponse:
    service = _build_service(session)
    try:
        job = service.update_job(job_id, **request.model_dump(exclude_unset=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SourcingJobResponse.model_validate(job)


@router.post("/{job_id}/run", response_model=RunJobResponse)
def run_job(
    job_id: str,
    _: None = Depends(verify_apps_script_secret),
    session: Session = DBSession,
) -> RunJobResponse:
    service = _build_service(session)
    try:
        result = service.run_job(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RunJobResponse.model_validate(result)
