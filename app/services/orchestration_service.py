from __future__ import annotations

from typing import Any

from app.domain.candidates import CandidateStatus, SourceCandidate
from app.integrations.sheets.base import SheetClient
from app.integrations.sheets.constants import SOURCE_CANDIDATES_TAB
from app.services.lead_enrich_and_draft_service import LeadEnrichAndDraftService
from app.services.promotion_service import PromotionService


class OrchestrationService:
    """Run the end-to-end sourcing workflow: candidates -> leads -> enrichment -> draft."""

    def __init__(self, sheet_client: SheetClient) -> None:
        self.sheet_client = sheet_client
        self.promotion_service = PromotionService(sheet_client)
        self.enrich_service = LeadEnrichAndDraftService(sheet_client)

    def run_end_to_end(
        self,
        *,
        job_run_id: str | None = None,
        candidate_ids: list[str] | None = None,
        run_id: str = "manual",
    ) -> dict[str, Any]:
        """Orchestrate the full pipeline for a set of candidates.

        If job_run_id is provided, only candidates with that import_batch_id
        are processed. If candidate_ids is provided, only those IDs are used.
        """
        candidates = self._load_candidates(
            job_run_id=job_run_id,
            candidate_ids=candidate_ids,
        )

        # Filter out duplicates and already promoted
        eligible = [
            c
            for c in candidates
            if c.candidate_status not in {
                CandidateStatus.DUPLICATE,
                CandidateStatus.PROMOTED_TO_LEAD,
            }
        ]

        promoted, rejected = self.promotion_service.evaluate_and_promote(eligible)

        # Enrich and draft the newly promoted leads
        enrichment_results = self.enrich_service.enrich_and_draft_leads(
            lead_ids=None,  # process all eligible leads
            run_id=run_id,
        )

        drafts_created = sum(
            1
            for r in enrichment_results
            if r.get("status") == "draft_ready" or r.get("email_draft")
        )

        return {
            "candidates_processed": len(eligible),
            "promoted": promoted,
            "rejected": rejected,
            "enrichment_results": len(enrichment_results),
            "drafts_created": drafts_created,
            "job_run_id": job_run_id,
            "run_id": run_id,
        }

    def _load_candidates(
        self,
        job_run_id: str | None = None,
        candidate_ids: list[str] | None = None,
    ) -> list[SourceCandidate]:
        import json

        rows = self.sheet_client.read_rows(tab_name=SOURCE_CANDIDATES_TAB)
        candidates = []
        for row in rows:
            values = dict(row.values)
            if not values.get("candidate_id"):
                continue
            if job_run_id and values.get("import_batch_id") != job_run_id:
                continue
            if candidate_ids and values.get("candidate_id") not in candidate_ids:
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
