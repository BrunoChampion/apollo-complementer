from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from googleapiclient.errors import HttpError
from pydantic import BaseModel, ConfigDict

from app.core.security import verify_apps_script_secret
from app.domain.candidates import CandidateStatus, SourceCandidate
from app.integrations.sheets.constants import SOURCE_CANDIDATES_TAB
from app.integrations.sheets.factory import build_sheet_client
from app.services.promotion_service import PromotionService
from app.services.readiness import validate_readiness

router = APIRouter(prefix="/candidates", tags=["candidates"])


class PromoteCandidatesRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source: str = "fake_sheet"
    sheet_id: str | None = None
    tab_name: str | None = None
    candidate_ids: list[str] | None = None


class PromoteCandidatesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    promoted_count: int
    rejected_count: int
    total_candidates: int


class ValidateCandidatesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    validated_count: int
    ready_count: int
    blocked_count: int
    total_candidates: int


def _load_candidates_from_rows(rows: list[Any]) -> list[SourceCandidate]:
    import json

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


@router.post("/validate", response_model=ValidateCandidatesResponse)
def validate_candidates(
    request: PromoteCandidatesRequest,
    _: None = Depends(verify_apps_script_secret),
) -> ValidateCandidatesResponse:
    sheet_client = build_sheet_client(
        source=request.source,
        sheet_id=request.sheet_id,
        tab_name=request.tab_name,
    )
    try:
        rows = sheet_client.read_rows(tab_name=SOURCE_CANDIDATES_TAB)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HttpError as exc:
        status_code = 429 if exc.resp.status == 429 else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    candidates = _load_candidates_from_rows(rows)
    if request.candidate_ids:
        id_set = set(request.candidate_ids)
        candidates = [c for c in candidates if c.candidate_id in id_set]

    rows_by_candidate_id = {
        row.values.get("candidate_id"): row.row_number
        for row in rows
        if row.values.get("candidate_id")
    }
    ready_count = 0
    blocked_count = 0
    for candidate in candidates:
        if candidate.candidate_status == CandidateStatus.DUPLICATE:
            continue
        readiness = validate_readiness(candidate)
        update_values = readiness.as_update()
        if readiness.ready_for_enrichment:
            candidate.candidate_status = CandidateStatus.READY_FOR_ENRICHMENT
            update_values["candidate_status"] = candidate.candidate_status.value
            ready_count += 1
        elif readiness.icp_status == "disqualified":
            candidate.candidate_status = CandidateStatus.DISQUALIFIED
            update_values["candidate_status"] = candidate.candidate_status.value
            blocked_count += 1
        else:
            candidate.candidate_status = CandidateStatus.NEEDS_REVIEW
            update_values["candidate_status"] = candidate.candidate_status.value
            blocked_count += 1
        row_number = rows_by_candidate_id.get(candidate.candidate_id)
        if row_number is not None:
            sheet_client.update_row(
                row_number=row_number,
                values=update_values,
                tab_name=SOURCE_CANDIDATES_TAB,
            )

    return ValidateCandidatesResponse(
        validated_count=ready_count + blocked_count,
        ready_count=ready_count,
        blocked_count=blocked_count,
        total_candidates=len(candidates),
    )


@router.post("/promote", response_model=PromoteCandidatesResponse)
def promote_candidates(
    request: PromoteCandidatesRequest,
    _: None = Depends(verify_apps_script_secret),
) -> PromoteCandidatesResponse:
    sheet_client = build_sheet_client(
        source=request.source,
        sheet_id=request.sheet_id,
        tab_name=request.tab_name,
    )

    try:
        rows = sheet_client.read_rows(tab_name=SOURCE_CANDIDATES_TAB)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HttpError as exc:
        status_code = 429 if exc.resp.status == 429 else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    candidates = _load_candidates_from_rows(rows)
    if request.candidate_ids:
        id_set = set(request.candidate_ids)
        candidates = [c for c in candidates if c.candidate_id in id_set]

    promotion_service = PromotionService(sheet_client)
    promoted, rejected = promotion_service.evaluate_and_promote(candidates)

    rows_by_candidate_id = {
        row.values.get("candidate_id"): row.row_number
        for row in rows
        if row.values.get("candidate_id")
    }
    update_statuses = {
        CandidateStatus.PROMOTED_TO_LEAD,
        CandidateStatus.NEEDS_REVIEW,
        CandidateStatus.DISQUALIFIED,
    }
    for candidate in candidates:
        if candidate.candidate_status not in update_statuses:
            continue
        row_number = rows_by_candidate_id.get(candidate.candidate_id)
        if row_number is None:
            continue
        update_values = {
            "candidate_status": candidate.candidate_status.value,
            "identity_validation_status": candidate.identity_validation_status,
            "identity_validation_reason": candidate.identity_validation_reason,
            "icp_status": candidate.icp_status,
            "icp_score": candidate.icp_score,
            "icp_score_reason": candidate.icp_score_reason,
            "ready_for_enrichment": candidate.ready_for_enrichment,
            "ready_for_draft": candidate.ready_for_draft,
        }
        sheet_client.update_row(
            row_number=row_number,
            values=update_values,
            tab_name=SOURCE_CANDIDATES_TAB,
        )

    return PromoteCandidatesResponse(
        promoted_count=promoted,
        rejected_count=rejected,
        total_candidates=len(candidates),
    )
