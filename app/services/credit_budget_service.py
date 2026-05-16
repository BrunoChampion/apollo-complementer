from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.db.repositories import ProviderUsageRepository


class BudgetExceededError(Exception):
    """Raised when a provider credit budget would be exceeded."""

    pass


class CreditBudgetService:
    """Track and enforce monthly credit budgets for external providers."""

    def __init__(
        self,
        repository: ProviderUsageRepository,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.settings = settings

    def check_budget(
        self,
        provider: str,
        estimated_credits: int,
    ) -> None:
        """Raise BudgetExceededError if estimated credits exceed monthly budget."""
        from datetime import UTC, datetime

        budget = self._budget_for_provider(provider)
        if budget <= 0:
            return  # No budget configured means unlimited

        now = datetime.now(UTC)
        used = self.repository.get_monthly_usage(
            provider=provider,
            year=now.year,
            month=now.month,
        )
        if used + estimated_credits > budget:
            remaining = budget - used
            raise BudgetExceededError(
                f"Provider '{provider}' monthly budget exceeded. "
                f"Used: {used}, Budget: {budget}, Remaining: {remaining}, "
                f"Requested: {estimated_credits}"
            )

    def record_usage(
        self,
        provider: str,
        credits_used: int,
        usage_type: str = "search",
        meta: dict[str, Any] | None = None,
    ) -> None:
        if credits_used <= 0:
            return
        self.repository.record_usage(
            provider=provider,
            usage_type=usage_type,
            credits_used=credits_used,
            meta=meta,
        )

    def estimate_search_credits(self, max_candidates: int) -> int:
        """Estimate Apollo search credits: 1 per page of 25 results."""
        import math

        return max(1, math.ceil(max_candidates / 25))

    def estimate_people_search_credits(self, max_candidates: int) -> int:
        """Apollo People API Search is currently documented as not consuming credits."""
        return 0

    def estimate_email_credits(self, candidate_count: int) -> int:
        """Each email enrichment costs 1 credit per candidate."""
        return candidate_count

    def _budget_for_provider(self, provider: str) -> int:
        if provider == "apollo":
            return self.settings.apollo_monthly_credit_budget
        if provider == "openai":
            return self.settings.openai_monthly_token_budget
        return 0
