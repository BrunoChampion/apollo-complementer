from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.core.security import verify_apps_script_secret
from app.integrations.sheets.factory import build_sheet_client
from app.services.lead_enrich_and_draft_service import LeadEnrichAndDraftService
from app.services.lead_enrichment_service import LeadEnrichmentService

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


class EnrichmentRunRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source: str = "fake_sheet"
    sheet_id: str | None = None
    tab_name: str | None = None
    lead_ids: list[str] | None = None
    run_id: str = "manual"
    force: bool = False


class EnrichmentRunResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    processed_count: int
    results: list[dict]


@router.post("/run", response_model=EnrichmentRunResponse)
def run_enrichment(
    request: EnrichmentRunRequest,
    _: None = Depends(verify_apps_script_secret),
) -> EnrichmentRunResponse:
    _validate_force_selection(request)
    sheet_client = build_sheet_client(
        source=request.source,
        sheet_id=request.sheet_id,
        tab_name=request.tab_name,
    )
    service = LeadEnrichmentService(sheet_client)
    results = service.enrich_leads(
        lead_ids=request.lead_ids,
        run_id=request.run_id,
        force=request.force,
    )
    return EnrichmentRunResponse(processed_count=len(results), results=results)


@router.post("/enrich_and_draft", response_model=EnrichmentRunResponse)
def run_enrich_and_draft(
    request: EnrichmentRunRequest,
    _: None = Depends(verify_apps_script_secret),
) -> EnrichmentRunResponse:
    _validate_force_selection(request)
    sheet_client = build_sheet_client(
        source=request.source,
        sheet_id=request.sheet_id,
        tab_name=request.tab_name,
    )
    service = LeadEnrichAndDraftService(sheet_client)
    results = service.enrich_and_draft_leads(
        lead_ids=request.lead_ids,
        run_id=request.run_id,
        force=request.force,
    )
    return EnrichmentRunResponse(processed_count=len(results), results=results)


@router.post("/draft", response_model=EnrichmentRunResponse)
def run_draft_from_enrichment(
    request: EnrichmentRunRequest,
    _: None = Depends(verify_apps_script_secret),
) -> EnrichmentRunResponse:
    sheet_client = build_sheet_client(
        source=request.source,
        sheet_id=request.sheet_id,
        tab_name=request.tab_name,
    )
    service = LeadEnrichAndDraftService(sheet_client)
    results = service.draft_leads(
        lead_ids=request.lead_ids,
        run_id=request.run_id,
    )
    return EnrichmentRunResponse(processed_count=len(results), results=results)


def _validate_force_selection(request: EnrichmentRunRequest) -> None:
    if request.force and not request.lead_ids:
        raise HTTPException(
            status_code=400,
            detail="force=true requires explicit lead_ids to avoid reprocessing all leads.",
        )
    settings = get_settings()
    if (
        request.force
        and request.lead_ids
        and len(request.lead_ids) > settings.enrichment_force_batch_limit
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "force=true is limited to "
                f"{settings.enrichment_force_batch_limit} selected leads per run."
            ),
        )


@router.post("/revise", response_model=EnrichmentRunResponse)
def run_enrichment_revise(
    request: EnrichmentRunRequest,
    _: None = Depends(verify_apps_script_secret),
) -> EnrichmentRunResponse:
    sheet_client = build_sheet_client(
        source=request.source,
        sheet_id=request.sheet_id,
        tab_name=request.tab_name,
    )
    service = LeadEnrichAndDraftService(sheet_client)
    results = service.revise_enriched_drafts(
        lead_ids=request.lead_ids,
        run_id=request.run_id,
    )
    return EnrichmentRunResponse(processed_count=len(results), results=results)


@router.post("/sync_from_leads", response_model=EnrichmentRunResponse)
def sync_enrichment_results_from_leads(
    request: EnrichmentRunRequest,
    _: None = Depends(verify_apps_script_secret),
) -> EnrichmentRunResponse:
    sheet_client = build_sheet_client(
        source=request.source,
        sheet_id=request.sheet_id,
        tab_name=request.tab_name,
    )
    service = LeadEnrichAndDraftService(sheet_client)
    results = service.sync_enrichment_results_from_leads(
        lead_ids=request.lead_ids,
        run_id=request.run_id,
    )
    return EnrichmentRunResponse(processed_count=len(results), results=results)
