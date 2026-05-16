from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class BatchLimits:
    manual_run_limit: int
    scheduled_batch_limit: int
    row_timeout_seconds: int
    max_revision_count_without_override: int


def get_batch_limits(settings: Settings | None = None) -> BatchLimits:
    settings = settings or get_settings()
    return BatchLimits(
        manual_run_limit=settings.manual_run_limit,
        scheduled_batch_limit=settings.scheduled_batch_limit,
        row_timeout_seconds=settings.row_timeout_seconds,
        max_revision_count_without_override=settings.max_revision_count_without_override,
    )
