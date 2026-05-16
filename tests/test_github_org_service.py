from datetime import UTC, datetime
from typing import Any

from app.graph.enrichment_tools import ENRICHMENT_TOOLS, github_search_org
from app.services.github_org_service import GitHubOrgService, build_org_candidates


class FakeResponse:
    def __init__(self, status_code: int, json_data: Any | None = None) -> None:
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> Any:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "https://api.github.com/test"),
                response=httpx.Response(self.status_code),
            )


class FakeGitHubClient:
    responses: dict[str, FakeResponse] = {}

    def __init__(self, **_: object) -> None:
        pass

    def __enter__(self) -> "FakeGitHubClient":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool | None:
        return None

    def get(self, path: str, params: dict[str, Any] | None = None) -> FakeResponse:
        return self.responses.get(path, FakeResponse(404))


def test_build_org_candidates_from_domain_and_name() -> None:
    candidates = build_org_candidates("https://www.acme.ai", "Acme Corp")

    assert candidates[:3] == ["acme", "acme-corp", "acme-io"]
    assert "acme-corp" in candidates
    assert len(candidates) == len(set(candidates))


def test_github_search_org_found(monkeypatch) -> None:
    import app.services.github_org_service as github_org_service

    FakeGitHubClient.responses = {
        "/orgs/acme": FakeResponse(200, {"login": "acme", "public_repos": 12}),
        "/orgs/acme/repos": FakeResponse(
            200,
            [
                {
                    "language": "Python",
                    "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                },
                {
                    "language": "TypeScript",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
                {
                    "language": "Python",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
            ],
        ),
    }
    monkeypatch.setattr(github_org_service.httpx, "Client", FakeGitHubClient)

    result = GitHubOrgService().search_org(company_domain="acme.com")

    assert result["org_found"] is True
    assert result["org_name"] == "acme"
    assert result["public_repos"] == 12
    assert result["top_languages"] == ["Python", "TypeScript"]
    assert result["recent_activity"] is True


def test_github_search_org_not_found(monkeypatch) -> None:
    import app.services.github_org_service as github_org_service

    FakeGitHubClient.responses = {}
    monkeypatch.setattr(github_org_service.httpx, "Client", FakeGitHubClient)

    result = GitHubOrgService().search_org(company_domain="missingco.com")

    assert result["org_found"] is False
    assert result["status"] == "ok"


def test_github_search_org_rate_limited(monkeypatch) -> None:
    import app.services.github_org_service as github_org_service

    FakeGitHubClient.responses = {"/orgs/acme": FakeResponse(403)}
    monkeypatch.setattr(github_org_service.httpx, "Client", FakeGitHubClient)

    result = GitHubOrgService().search_org(company_domain="acme.com")

    assert result["org_found"] is False
    assert result["status"] == "rate_limited"


def test_github_search_org_tool_wrapper(monkeypatch) -> None:
    import app.services.github_org_service as github_org_service

    FakeGitHubClient.responses = {
        "/orgs/acme": FakeResponse(200, {"login": "acme", "public_repos": 1}),
        "/orgs/acme/repos": FakeResponse(200, []),
    }
    monkeypatch.setattr(github_org_service.httpx, "Client", FakeGitHubClient)

    if hasattr(github_search_org, "invoke"):
        result = github_search_org.invoke({"company_domain": "acme.com"})
    else:
        result = github_search_org("acme.com")

    assert result["org_found"] is True
    assert github_search_org in ENRICHMENT_TOOLS
