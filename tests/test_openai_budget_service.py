import pytest

from app.core.config import Settings
from app.db.repositories import ProviderUsageRepository
from app.services.credit_budget_service import BudgetExceededError, CreditBudgetService
from tests.db_utils import build_test_session


def test_openai_budget_uses_token_budget() -> None:
    session = next(build_test_session())
    service = CreditBudgetService(
        repository=ProviderUsageRepository(session),
        settings=Settings(openai_monthly_token_budget=1000),
    )

    service.record_usage("openai", 400, "tokens")
    service.check_budget("openai", 600)

    with pytest.raises(BudgetExceededError):
        service.check_budget("openai", 601)


def test_zero_openai_budget_means_unlimited() -> None:
    session = next(build_test_session())
    service = CreditBudgetService(
        repository=ProviderUsageRepository(session),
        settings=Settings(openai_monthly_token_budget=0),
    )

    service.check_budget("openai", 999_999)
