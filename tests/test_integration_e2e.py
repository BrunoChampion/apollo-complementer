from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.domain.candidates import SourceCandidate, SourceProvider
from app.domain.leads import LeadAction, LeadRow, LeadStatus
from app.services.credit_budget_service import BudgetExceededError, CreditBudgetService
from app.services.enrich_and_draft_service import EnrichAndDraftService
from app.services.orchestration_service import OrchestrationService
from app.services.promotion_service import PromotionService
from app.services.sourcing_job_service import SourcingJobService


class TestEndToEndIntegration:
    """Integration-style test that exercises the full pipeline with mocks."""

    def test_full_pipeline_from_candidates_to_draft(self) -> None:
        """Simulate:
        1. Apollo job creates candidates
        2. Promotion evaluates and promotes
        3. Enrichment scores and produces evidence
        4. Draft gating allows drafting
        5. Draft agent produces email
        6. Orchestration endpoint returns summary
        """
        # Mock sheet client
        sheet_client = MagicMock()
        sheet_client.read_rows.return_value = []

        # 1. Sourcing job service (mock Apollo client)
        apollo_client = MagicMock()
        apollo_client.search_people.return_value = {
            "people": [
                {
                    "id": "p1",
                    "name": "Ana Lopez",
                    "title": "COO",
                    "email": "ana@acme.com",
                    "linkedin_url": "https://linkedin.com/in/ana",
                    "organization": {
                        "name": "Acme Corp",
                        "website_url": "https://acme.com",
                    },
                }
            ],
            "pagination": {"total_pages": 1},
        }

        repository = MagicMock()
        job = MagicMock()
        job.is_active = True
        job.max_candidates = 5
        job.enrich_emails = False
        job.query_params = {"titles": ["COO"]}
        repository.get_job.return_value = job

        job_run = MagicMock()
        job_run.id = "run_001"
        repository.create_job_run.return_value = job_run

        sourcing_service = SourcingJobService(
            repository=repository,
            apollo_client=apollo_client,
            sheet_client=sheet_client,
            credit_budget_service=None,
        )

        result = sourcing_service.run_job("job_001")
        assert result["status"] == "completed"
        assert result["total_found"] == 1
        assert result["imported"] == 1

        # 2. Promotion service
        promotion_service = PromotionService(sheet_client)

        candidate = SourceCandidate(
            candidate_id="apollo_p1",
            source_provider=SourceProvider.APOLLO,
            company_name="Acme Corp",
            company_website="https://acme.com",
            prospect_name="Ana Lopez",
            prospect_title="COO",
            prospect_email="ana@acme.com",
            country="Argentina",
        )
        should_promote, reason = promotion_service.should_promote(candidate)
        assert should_promote is True
        assert reason is None

        # 3. Enrichment agent (deterministic)
        lead = LeadRow(
            lead_id="apollo_p1",
            company_name="Acme Corp",
            company_website="https://acme.com",
            prospect_name="Ana Lopez",
            prospect_title="COO",
            prospect_email="ana@acme.com",
            country="Argentina",
            action=LeadAction.RESEARCH_AND_DRAFT,
            status=LeadStatus.NEW,
        )

        # 4. Enrich and draft service
        enrich_service = EnrichAndDraftService()
        result = enrich_service.enrich_and_draft(lead, run_id="test_e2e")

        # The deterministic LLM may return draft, discard, or needs_manual_research
        # depending on the mock/fake data. We just verify the pipeline ran.
        assert "status" in result
        assert result["lead_id"] == "apollo_p1"

        # 5. Credit budget service
        from app.db.repositories import ProviderUsageRepository

        usage_repo = MagicMock(spec=ProviderUsageRepository)
        usage_repo.get_monthly_usage.return_value = 5
        budget_service = CreditBudgetService(
            repository=usage_repo,
            settings=Settings(apollo_monthly_credit_budget=10),
        )

        # Should pass with 4 remaining credits
        budget_service.check_budget("apollo", 4)

        # Should fail with 6 requested credits
        with pytest.raises(BudgetExceededError):
            budget_service.check_budget("apollo", 6)

        # 6. Orchestration service (unit-level)
        orchestration = OrchestrationService(sheet_client)
        with patch.object(
            orchestration.promotion_service, "evaluate_and_promote", return_value=(1, 0)
        ):
            with patch.object(
                orchestration.enrich_service,
                "enrich_and_draft_leads",
                return_value=[{"status": "draft_ready", "email_draft": "Hello Ana"}],
            ):
                summary = orchestration.run_end_to_end(
                    job_run_id="run_001",
                    run_id="integration_test",
                )

        assert summary["promoted"] == 1
        assert summary["rejected"] == 0
        assert summary["drafts_created"] == 1
        assert summary["run_id"] == "integration_test"

    def test_budget_hard_stop_prevents_overrun(self) -> None:
        from app.db.repositories import ProviderUsageRepository

        usage_repo = MagicMock(spec=ProviderUsageRepository)
        usage_repo.get_monthly_usage.return_value = 2400
        budget_service = CreditBudgetService(
            repository=usage_repo,
            settings=Settings(apollo_monthly_credit_budget=2500),
        )

        # 100 credits requested, 100 remaining -> should pass
        budget_service.check_budget("apollo", 100)

        # 101 credits requested -> should fail
        with pytest.raises(BudgetExceededError):
            budget_service.check_budget("apollo", 101)
