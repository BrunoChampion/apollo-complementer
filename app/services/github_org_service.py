from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings

GITHUB_API_BASE_URL = "https://api.github.com"


@dataclass(frozen=True)
class GitHubOrgResult:
    org_found: bool
    org_name: str | None
    public_repos: int
    top_languages: list[str]
    recent_activity: bool
    status: str = "ok"
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "org_found": self.org_found,
            "org_name": self.org_name,
            "public_repos": self.public_repos,
            "top_languages": self.top_languages,
            "recent_activity": self.recent_activity,
            "status": self.status,
            "error": self.error,
        }


class GitHubOrgService:
    """Best-effort GitHub organization discovery for a prospect company."""

    def __init__(self, *, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    def search_org(
        self,
        *,
        company_domain: str,
        company_name: str | None = None,
    ) -> dict[str, Any]:
        candidates = build_org_candidates(company_domain, company_name)
        if not candidates:
            return _not_found().as_dict()

        headers = _github_headers()
        try:
            with httpx.Client(
                base_url=GITHUB_API_BASE_URL,
                timeout=self.timeout_seconds,
                headers=headers,
            ) as client:
                for candidate in candidates:
                    org_response = client.get(f"/orgs/{candidate}")
                    if org_response.status_code == 404:
                        continue
                    if org_response.status_code in {403, 429}:
                        return _not_found(
                            status="rate_limited",
                            error=f"GitHub API returned {org_response.status_code}",
                        ).as_dict()
                    try:
                        org_response.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        return _not_found(status="error", error=str(exc)).as_dict()

                    org_data = org_response.json()
                    repos = _fetch_repositories(client, candidate)
                    return _build_found_result(org_data, repos).as_dict()
        except httpx.RequestError as exc:
            return _not_found(status="error", error=str(exc)).as_dict()

        return _not_found().as_dict()


def github_search_org_data(
    company_domain: str,
    company_name: str | None = None,
) -> dict[str, Any]:
    return GitHubOrgService().search_org(
        company_domain=company_domain,
        company_name=company_name,
    )


def build_org_candidates(company_domain: str | None, company_name: str | None = None) -> list[str]:
    candidates: list[str] = []
    domain_base = _domain_base(company_domain)
    if domain_base:
        candidates.append(domain_base)
        candidates.append(f"{domain_base}-corp")
        candidates.append(f"{domain_base}-io")

    name_slug = _slugify(company_name)
    if name_slug:
        candidates.append(name_slug)
        candidates.append(f"{name_slug}-corp")

    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def _fetch_repositories(client: httpx.Client, org_name: str) -> list[dict[str, Any]]:
    response = client.get(f"/orgs/{org_name}/repos", params={"per_page": 30, "sort": "updated"})
    if response.status_code in {403, 429, 404}:
        return []
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def _build_found_result(org_data: dict[str, Any], repos: list[dict[str, Any]]) -> GitHubOrgResult:
    languages = Counter(
        str(repo.get("language"))
        for repo in repos
        if repo.get("language")
    )
    recent_cutoff = datetime.now(UTC) - timedelta(days=180)
    recent_activity = any(
        _parse_github_datetime(repo.get("updated_at")) >= recent_cutoff
        for repo in repos
    )
    public_repos = org_data.get("public_repos")
    if not isinstance(public_repos, int):
        public_repos = len(repos)
    return GitHubOrgResult(
        org_found=True,
        org_name=org_data.get("login"),
        public_repos=public_repos,
        top_languages=[language for language, _ in languages.most_common(5)],
        recent_activity=recent_activity,
    )


def _github_headers() -> dict[str, str]:
    settings = get_settings()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "NYVEX-RevenueOpsCopilot/1.0",
    }
    if settings.github_api_token:
        headers["Authorization"] = f"Bearer {settings.github_api_token}"
    return headers


def _domain_base(domain: str | None) -> str:
    value = (domain or "").strip().lower()
    if not value:
        return ""
    if "://" in value:
        parsed = urlparse(value)
        value = parsed.netloc or parsed.path
    value = value.removeprefix("www.")
    return _slugify(value.split(".")[0])


def _slugify(value: str | None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug


def _parse_github_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=UTC)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)


def _not_found(status: str = "ok", error: str | None = None) -> GitHubOrgResult:
    return GitHubOrgResult(
        org_found=False,
        org_name=None,
        public_repos=0,
        top_languages=[],
        recent_activity=False,
        status=status,
        error=error,
    )
