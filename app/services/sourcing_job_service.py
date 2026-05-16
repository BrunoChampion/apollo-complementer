from __future__ import annotations

from typing import Any

from app.db.repositories import SourcingJobRepository
from app.domain.candidates import SourceCandidate, SourceProvider
from app.integrations.apollo import ApolloClient
from app.integrations.sheets.base import SheetClient
from app.integrations.sheets.constants import SOURCE_CANDIDATES_HEADERS, SOURCE_CANDIDATES_TAB
from app.services.apollo_enrichment_policy import ApolloEmailEnrichmentPolicy
from app.services.credit_budget_service import CreditBudgetService
from app.services.dedupe_service import DedupeService
from app.services.flexible_match import normalize_domain


class SourcingJobService:
    """Run sourcing jobs using Apollo and save candidates."""

    def __init__(
        self,
        repository: SourcingJobRepository,
        apollo_client: ApolloClient,
        sheet_client: SheetClient,
        credit_budget_service: CreditBudgetService | None = None,
        email_enrichment_policy: ApolloEmailEnrichmentPolicy | None = None,
    ) -> None:
        self.repository = repository
        self.apollo = apollo_client
        self.sheet_client = sheet_client
        self.credit_budget_service = credit_budget_service
        self.email_enrichment_policy = (
            email_enrichment_policy or ApolloEmailEnrichmentPolicy()
        )

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
    ) -> Any:
        return self.repository.create_job(
            name=name,
            description=description,
            provider=provider,
            query_params=query_params,
            max_candidates=max_candidates,
            enrich_emails=enrich_emails,
            created_by=created_by,
        )

    def list_jobs(self) -> list[Any]:
        return self.repository.list_jobs()

    def get_job(self, job_id: str) -> Any | None:
        return self.repository.get_job(job_id)

    def update_job(
        self,
        job_id: str,
        **kwargs: Any,
    ) -> Any:
        return self.repository.update_job(job_id, **kwargs)

    def run_job(self, job_id: str) -> dict[str, Any]:
        job = self.repository.get_job(job_id)
        if job is None:
            raise LookupError(f"Sourcing job not found: {job_id}")
        if not job.is_active:
            raise ValueError(f"Sourcing job is inactive: {job_id}")

        job_run = self.repository.create_job_run(job_id=job_id, status="running")
        query = job.query_params or {}

        if self.credit_budget_service is not None:
            estimated_search = self.credit_budget_service.estimate_people_search_credits(
                job.max_candidates
            )
            estimated_email = 0
            if job.enrich_emails:
                estimated_email = 1
            self.credit_budget_service.check_budget(
                "apollo",
                estimated_search + estimated_email,
            )

        try:
            candidates_found = self._execute_apollo_search(
                query=query,
                max_candidates=job.max_candidates,
                enrich_emails=job.enrich_emails,
                job_run_id=job_run.id,
            )
        except Exception as exc:
            self.repository.finish_job_run(
                run_id=job_run.id,
                status="failed",
                error_message=str(exc),
            )
            raise

        if self.credit_budget_service is not None:
            search_pages = self.credit_budget_service.estimate_people_search_credits(
                candidates_found["total_found"]
            )
            self.credit_budget_service.record_usage(
                provider="apollo",
                credits_used=search_pages,
                usage_type="search",
                meta={"job_id": job_id, "job_run_id": job_run.id},
            )
            if candidates_found["apollo_enrichment_credits_used"] > 0:
                self.credit_budget_service.record_usage(
                    provider="apollo",
                    credits_used=candidates_found["apollo_enrichment_credits_used"],
                    usage_type="email_enrichment",
                    meta={"job_id": job_id, "job_run_id": job_run.id},
                )

        self.repository.finish_job_run(
            run_id=job_run.id,
            status="completed",
            candidates_found=candidates_found["total_found"],
            candidates_imported=candidates_found["imported"],
            candidates_duplicated=candidates_found["duplicated"],
            candidates_rejected=candidates_found["rejected"],
            summary=candidates_found,
        )

        return {
            "job_id": job_id,
            "job_run_id": job_run.id,
            "status": "completed",
            **candidates_found,
        }

    def _execute_apollo_search(
        self,
        query: dict[str, Any],
        max_candidates: int,
        enrich_emails: bool,
        job_run_id: str | None = None,
    ) -> dict[str, Any]:
        page = 1
        per_page = min(25, max_candidates)
        total_found = 0
        imported = 0
        duplicated = 0
        rejected = 0
        emails_enriched = 0
        apollo_enrichment_credits_used = 0

        existing = self._load_existing_candidates()
        dedupe = DedupeService(existing)

        while total_found < max_candidates:
            result = self.apollo.search_people(
                q_keywords=query.get("keywords"),
                person_titles=query.get("titles"),
                person_locations=query.get("countries"),
                page=page,
                per_page=per_page,
            )
            people = result.get("people", [])
            pagination = result.get("pagination", {})

            if not people:
                break

            for person in people:
                if total_found >= max_candidates:
                    break
                total_found += 1

                candidate = self._person_to_candidate(person, enrich_emails, job_run_id)
                dup = dedupe.find_duplicate(candidate)
                if dup:
                    dedupe.mark_duplicate(candidate, dup)
                    duplicated += 1
                    continue

                if enrich_emails:
                    candidate, email_found, credits_used = self._maybe_enrich_email(candidate)
                    emails_enriched += email_found
                    apollo_enrichment_credits_used += credits_used

                candidate.dedupe_key = dedupe.generate_dedupe_key(candidate)
                self._write_candidate(candidate)
                imported += 1

            if page >= pagination.get("total_pages", 1):
                break
            page += 1

        return {
            "total_found": total_found,
            "imported": imported,
            "duplicated": duplicated,
            "rejected": rejected,
            "emails_enriched": emails_enriched,
            "apollo_enrichment_credits_used": apollo_enrichment_credits_used,
        }

    def _person_to_candidate(
        self,
        person: dict[str, Any],
        enrich_emails: bool,
        job_run_id: str | None = None,
    ) -> SourceCandidate:
        org = person.get("organization") or {}
        location = org.get("location") or {}
        company_domain = normalize_domain(
            org.get("website_url") or org.get("primary_domain") or person.get("domain")
        )
        return SourceCandidate(
            candidate_id=f"apollo_{person.get('id', 'unknown')}",
            source_provider=SourceProvider.APOLLO,
            source_record_id=person.get("id"),
            company_name=org.get("name"),
            company_website=org.get("website_url"),
            company_domain=company_domain or None,
            company_linkedin_url=org.get("linkedin_url"),
            prospect_name=person.get("name"),
            prospect_title=person.get("title"),
            prospect_email=person.get("email") if enrich_emails else None,
            prospect_linkedin_url=person.get("linkedin_url"),
            country=(
                person.get("country")
                or person.get("person_country")
                or location.get("country")
                or org.get("country")
            ),
            region=person.get("state") or location.get("state"),
            industry=org.get("industry"),
            company_size=str(org.get("estimated_num_employees") or "")
            if org.get("estimated_num_employees") is not None
            else None,
            raw_data_json=person,
            import_batch_id=job_run_id,
        )

    def _maybe_enrich_email(
        self, candidate: SourceCandidate
    ) -> tuple[SourceCandidate, int, int]:
        decision = self.email_enrichment_policy.evaluate(candidate)
        candidate.apollo_enrichment_score = decision.score
        candidate.apollo_enrichment_confidence = decision.confidence
        candidate.apollo_enrichment_reason = decision.reason

        if not decision.should_enrich:
            candidate.apollo_enrichment_status = "skipped"
            candidate.apollo_credits_used = 0
            return candidate, 0, 0

        if self.credit_budget_service is not None:
            self.credit_budget_service.check_budget("apollo", decision.estimated_credits)

        response = self.apollo.enrich_person(
            id=candidate.source_record_id,
            name=candidate.prospect_name,
            domain=candidate.company_domain,
            linkedin_url=candidate.prospect_linkedin_url,
        )
        person = response.get("person") or {}
        enriched_email = person.get("email")
        if enriched_email:
            from datetime import UTC, datetime

            candidate.prospect_email = enriched_email
            candidate.apollo_enrichment_status = "enriched"
            candidate.apollo_email_enriched_at = datetime.now(UTC).isoformat()
            candidate.apollo_credits_used = decision.estimated_credits
            return candidate, 1, decision.estimated_credits

        candidate.apollo_enrichment_status = "no_email_found"
        candidate.apollo_credits_used = decision.estimated_credits
        return candidate, 0, decision.estimated_credits

    def _load_existing_candidates(self) -> list[SourceCandidate]:
        import json

        rows = self.sheet_client.read_rows(tab_name=SOURCE_CANDIDATES_TAB)
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

    def _write_candidate(self, candidate: SourceCandidate) -> None:
        self.sheet_client.append_row(
            tab_name=SOURCE_CANDIDATES_TAB,
            values=candidate.model_dump(mode="json"),
            headers=SOURCE_CANDIDATES_HEADERS,
        )
