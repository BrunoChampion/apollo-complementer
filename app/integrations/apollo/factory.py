from app.core.config import Settings
from app.integrations.apollo.fake import FakeApolloClient
from app.integrations.apollo.http import HttpApolloClient


def build_apollo_client(settings: Settings) -> FakeApolloClient | HttpApolloClient:
    if not _is_real_secret(settings.apollo_api_key):
        return FakeApolloClient(min_candidate_score=settings.apollo_min_candidate_score)
    return HttpApolloClient(
        api_key=settings.apollo_api_key,
        base_url=settings.apollo_base_url,
    )


def _is_real_secret(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.strip().lower()
    return not (
        normalized.startswith("replace-with")
        or normalized.startswith("generate-")
        or normalized in {"changeme", "change-me", "todo", "none", "null"}
    )
