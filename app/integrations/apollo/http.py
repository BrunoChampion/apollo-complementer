from __future__ import annotations

from typing import Any

import httpx

DEFAULT_TIMEOUT_SECONDS = 30
MAX_RETRIES = 2


class HttpApolloClient:
    """Real Apollo API client with rate limiting and timeout handling."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.apollo.io",
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
        }

        for attempt in range(MAX_RETRIES + 1):
            try:
                if method.lower() == "get":
                    response = httpx.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=self.timeout_seconds,
                    )
                else:
                    response = httpx.post(
                        url,
                        headers=headers,
                        params=params,
                        json=json_body,
                        timeout=self.timeout_seconds,
                    )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt < MAX_RETRIES:
                    import time

                    time.sleep(2 ** attempt)
                    continue
                raise
            except httpx.RequestError:
                if attempt < MAX_RETRIES:
                    import time

                    time.sleep(2 ** attempt)
                    continue
                raise

        return {}

    def search_people(
        self,
        *,
        q_keywords: str | None = None,
        organization_ids: list[str] | None = None,
        person_titles: list[str] | None = None,
        person_locations: list[str] | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "page": page,
            "per_page": min(per_page, 100),
        }
        if q_keywords:
            body["q_keywords"] = q_keywords
        if organization_ids:
            body["organization_ids"] = organization_ids
        if person_titles:
            body["person_titles"] = person_titles
        if person_locations:
            body["person_locations"] = person_locations

        return self._request("post", "/api/v1/mixed_people/api_search", params=body)

    def search_companies(
        self,
        *,
        q_organization_name: str | None = None,
        organization_locations: list[str] | None = None,
        organization_num_employees_range: list[int] | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "page": page,
            "per_page": min(per_page, 100),
        }
        if q_organization_name:
            body["q_organization_name"] = q_organization_name
        if organization_locations:
            body["organization_locations"] = organization_locations
        if organization_num_employees_range:
            body["organization_num_employees_range"] = organization_num_employees_range

        return self._request("post", "/api/v1/mixed_companies/search", params=body)

    def enrich_organization(
        self,
        *,
        domain: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if domain:
            params["domain"] = domain
        if name:
            params["name"] = name

        return self._request("get", "/api/v1/organizations/enrich", params=params)

    def enrich_person(
        self,
        *,
        id: str | None = None,
        name: str | None = None,
        email: str | None = None,
        domain: str | None = None,
        linkedin_url: str | None = None,
        reveal_personal_emails: bool = False,
        reveal_phone_number: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if id:
            params["id"] = id
        if name:
            params["name"] = name
        if email:
            params["email"] = email
        if domain:
            params["domain"] = domain
        if linkedin_url:
            params["linkedin_url"] = linkedin_url
        if reveal_personal_emails:
            params["reveal_personal_emails"] = True
        if reveal_phone_number:
            params["reveal_phone_number"] = True

        return self._request("post", "/api/v1/people/match", params=params)
