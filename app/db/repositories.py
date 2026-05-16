from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    EnrichmentEvidenceItem,
    EnrichmentRun,
    EvidenceItem,
    LeadRun,
    ProviderUsage,
    Run,
    SourcingJob,
    SourcingJobRun,
)


class RunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_run(
        self,
        *,
        source: str,
        sheet_id: str | None = None,
        created_by: str | None = None,
    ) -> Run:
        run = Run(source=source, sheet_id=sheet_id, created_by=created_by, status="queued")
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get_run(self, run_id: str) -> Run | None:
        return self.session.get(Run, run_id)

    def list_lead_runs(self, run_id: str) -> list[LeadRun]:
        return list(
            self.session.scalars(
                select(LeadRun).where(LeadRun.run_id == run_id).order_by(LeadRun.started_at)
            )
        )

    def update_run_status(self, run_id: str, status: str) -> Run:
        run = self._require_run(run_id)
        run.status = status
        self.session.commit()
        self.session.refresh(run)
        return run

    def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        total_rows: int,
        success_count: int,
        error_count: int,
        summary: dict[str, Any],
    ) -> Run:
        run = self._require_run(run_id)
        run.status = status
        run.total_rows = total_rows
        run.success_count = success_count
        run.error_count = error_count
        run.summary = summary
        run.finished_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(run)
        return run

    def create_lead_run(
        self,
        *,
        run_id: str,
        lead_id: str,
        row_number: int | None,
        action: str,
        status: str,
        input_snapshot: dict[str, Any] | None = None,
        output_snapshot: dict[str, Any] | None = None,
        error_message: str | None = None,
        finished: bool = False,
    ) -> LeadRun:
        lead_run = LeadRun(
            run_id=run_id,
            lead_id=lead_id,
            row_number=row_number,
            action=action,
            status=status,
            input_snapshot=input_snapshot,
            output_snapshot=output_snapshot,
            error_message=error_message,
            finished_at=datetime.now(UTC) if finished else None,
        )
        self.session.add(lead_run)
        self.session.commit()
        self.session.refresh(lead_run)
        return lead_run

    def create_evidence_item(
        self,
        *,
        lead_run_id: str,
        lead_id: str,
        claim: str,
        source_type: str,
        confidence: str,
        source_url: str | None = None,
        used_in_message: bool = False,
    ) -> EvidenceItem:
        evidence_item = EvidenceItem(
            lead_run_id=lead_run_id,
            lead_id=lead_id,
            claim=claim,
            source_type=source_type,
            source_url=source_url,
            confidence=confidence,
            used_in_message=used_in_message,
        )
        self.session.add(evidence_item)
        self.session.commit()
        self.session.refresh(evidence_item)
        return evidence_item

    def list_evidence_items(self, lead_run_id: str) -> list[EvidenceItem]:
        return list(
            self.session.scalars(
                select(EvidenceItem)
                .where(EvidenceItem.lead_run_id == lead_run_id)
                .order_by(EvidenceItem.created_at)
            )
        )

    def _require_run(self, run_id: str) -> Run:
        run = self.get_run(run_id)
        if run is None:
            raise LookupError(f"Run not found: {run_id}")
        return run


class EnrichmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_enrichment_run(
        self,
        *,
        run_id: str | None = None,
        lead_id: str | None = None,
        status: str = "pending",
        company_summary: str | None = None,
        b2b_fit: bool | None = None,
        operational_pain_hypothesis: str | None = None,
        possible_ai_use_case: str | None = None,
        personalization_angle: str | None = None,
        trigger_summary: str | None = None,
        risk_flags: list[str] | None = None,
        confidence_score: int | None = None,
        recommended_action: str | None = None,
        error_message: str | None = None,
    ) -> EnrichmentRun:
        enrichment = EnrichmentRun(
            run_id=run_id,
            lead_id=lead_id,
            status=status,
            company_summary=company_summary,
            b2b_fit=b2b_fit,
            operational_pain_hypothesis=operational_pain_hypothesis,
            possible_ai_use_case=possible_ai_use_case,
            personalization_angle=personalization_angle,
            trigger_summary=trigger_summary,
            risk_flags=risk_flags,
            confidence_score=confidence_score,
            recommended_action=recommended_action,
            error_message=error_message,
        )
        self.session.add(enrichment)
        self.session.commit()
        self.session.refresh(enrichment)
        return enrichment

    def get_enrichment_run(self, enrichment_id: str) -> EnrichmentRun | None:
        return self.session.get(EnrichmentRun, enrichment_id)

    def finish_enrichment_run(
        self,
        enrichment_id: str,
        *,
        status: str,
        error_message: str | None = None,
    ) -> EnrichmentRun:
        enrichment = self._require_enrichment_run(enrichment_id)
        enrichment.status = status
        enrichment.error_message = error_message
        enrichment.finished_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(enrichment)
        return enrichment

    def create_evidence_item(
        self,
        *,
        enrichment_run_id: str,
        claim: str,
        source_type: str,
        source_url: str | None = None,
        quote_or_summary: str | None = None,
        confidence: int = 50,
        used_in_message: bool = False,
    ) -> EnrichmentEvidenceItem:
        item = EnrichmentEvidenceItem(
            enrichment_run_id=enrichment_run_id,
            claim=claim,
            source_type=source_type,
            source_url=source_url,
            quote_or_summary=quote_or_summary,
            confidence=confidence,
            used_in_message=used_in_message,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list_evidence_items(self, enrichment_run_id: str) -> list[EnrichmentEvidenceItem]:
        return list(
            self.session.scalars(
                select(EnrichmentEvidenceItem)
                .where(EnrichmentEvidenceItem.enrichment_run_id == enrichment_run_id)
                .order_by(EnrichmentEvidenceItem.created_at)
            )
        )

    def _require_enrichment_run(self, enrichment_id: str) -> EnrichmentRun:
        enrichment = self.get_enrichment_run(enrichment_id)
        if enrichment is None:
            raise LookupError(f"Enrichment run not found: {enrichment_id}")


class SourcingJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_job(
        self,
        *,
        name: str,
        description: str | None = None,
        provider: str = "apollo",
        query_params: dict[str, Any] | None = None,
        max_candidates: int = 50,
        enrich_emails: bool = False,
        created_by: str | None = None,
    ) -> SourcingJob:
        job = SourcingJob(
            name=name,
            description=description,
            provider=provider,
            query_params=query_params,
            max_candidates=max_candidates,
            enrich_emails=enrich_emails,
            created_by=created_by,
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get_job(self, job_id: str) -> SourcingJob | None:
        return self.session.get(SourcingJob, job_id)

    def list_jobs(self) -> list[SourcingJob]:
        return list(
            self.session.scalars(
                select(SourcingJob)
                .where(SourcingJob.is_active)
                .order_by(SourcingJob.created_at.desc())
            )
        )

    def update_job(
        self,
        job_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        query_params: dict[str, Any] | None = None,
        max_candidates: int | None = None,
        enrich_emails: bool | None = None,
        is_active: bool | None = None,
    ) -> SourcingJob:
        job = self._require_job(job_id)
        if name is not None:
            job.name = name
        if description is not None:
            job.description = description
        if query_params is not None:
            job.query_params = query_params
        if max_candidates is not None:
            job.max_candidates = max_candidates
        if enrich_emails is not None:
            job.enrich_emails = enrich_emails
        if is_active is not None:
            job.is_active = is_active
        self.session.commit()
        self.session.refresh(job)
        return job

    def create_job_run(
        self,
        *,
        job_id: str,
        status: str = "queued",
    ) -> SourcingJobRun:
        run = SourcingJobRun(job_id=job_id, status=status)
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def finish_job_run(
        self,
        run_id: str,
        *,
        status: str,
        candidates_found: int = 0,
        candidates_imported: int = 0,
        candidates_duplicated: int = 0,
        candidates_rejected: int = 0,
        error_message: str | None = None,
        summary: dict[str, Any] | None = None,
    ) -> SourcingJobRun:
        run = self.session.get(SourcingJobRun, run_id)
        if run is None:
            raise LookupError(f"Sourcing job run not found: {run_id}")
        run.status = status
        run.candidates_found = candidates_found
        run.candidates_imported = candidates_imported
        run.candidates_duplicated = candidates_duplicated
        run.candidates_rejected = candidates_rejected
        run.error_message = error_message
        run.summary = summary
        run.finished_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(run)
        return run

    def _require_job(self, job_id: str) -> SourcingJob:
        job = self.get_job(job_id)
        if job is None:
            raise LookupError(f"Sourcing job not found: {job_id}")
        return job


class ProviderUsageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record_usage(
        self,
        *,
        provider: str,
        usage_type: str,
        credits_used: int = 1,
        meta: dict[str, Any] | None = None,
    ) -> ProviderUsage:
        usage = ProviderUsage(
            provider=provider,
            usage_type=usage_type,
            credits_used=credits_used,
            meta=meta,
        )
        self.session.add(usage)
        self.session.commit()
        self.session.refresh(usage)
        return usage

    def get_monthly_usage(self, provider: str, year: int, month: int) -> int:
        from sqlalchemy import extract, func

        total = self.session.scalar(
            select(func.coalesce(func.sum(ProviderUsage.credits_used), 0)).where(
                ProviderUsage.provider == provider,
                extract("year", ProviderUsage.created_at) == year,
                extract("month", ProviderUsage.created_at) == month,
            )
        )
        return total or 0
