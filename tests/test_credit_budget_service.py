from datetime import UTC, datetime

import pytest

from app.core.config import Settings
from app.db.repositories import ProviderUsageRepository
from app.services.credit_budget_service import BudgetExceededError, CreditBudgetService
from tests.db_utils import build_test_session


def _service(session) -> CreditBudgetService:
    settings = Settings(apollo_monthly_credit_budget=10)
    return CreditBudgetService(
        repository=ProviderUsageRepository(session),
        settings=settings,
    )


class TestCreditBudgetService:
    def test_record_usage_and_get_monthly_usage(self) -> None:
        session = next(build_test_session())
        service = _service(session)
        service.record_usage("apollo", 3, "search")
        service.record_usage("apollo", 2, "email_enrichment")

        now = datetime.now(UTC)
        total = service.repository.get_monthly_usage("apollo", now.year, now.month)
        assert total == 5

    def test_check_budget_passes_when_under(self) -> None:
        session = next(build_test_session())
        service = _service(session)
        service.record_usage("apollo", 5, "search")
        # budget is 10, used 5, requesting 4 -> ok
        service.check_budget("apollo", 4)

    def test_check_budget_raises_when_exceeded(self) -> None:
        session = next(build_test_session())
        service = _service(session)
        service.record_usage("apollo", 8, "search")
        with pytest.raises(BudgetExceededError):
            service.check_budget("apollo", 5)

    def test_estimate_search_credits(self) -> None:
        session = next(build_test_session())
        service = _service(session)
        assert service.estimate_search_credits(10) == 1
        assert service.estimate_search_credits(25) == 1
        assert service.estimate_search_credits(26) == 2
        assert service.estimate_search_credits(50) == 2
        assert service.estimate_search_credits(51) == 3

    def test_estimate_people_search_credits_is_free(self) -> None:
        session = next(build_test_session())
        service = _service(session)
        assert service.estimate_people_search_credits(100) == 0

    def test_estimate_email_credits(self) -> None:
        session = next(build_test_session())
        service = _service(session)
        assert service.estimate_email_credits(5) == 5
        assert service.estimate_email_credits(0) == 0

    def test_zero_budget_means_unlimited(self) -> None:
        session = next(build_test_session())
        settings = Settings(apollo_monthly_credit_budget=0)
        service = CreditBudgetService(
            repository=ProviderUsageRepository(session),
            settings=settings,
        )
        service.record_usage("apollo", 999, "search")
        service.check_budget("apollo", 999)
