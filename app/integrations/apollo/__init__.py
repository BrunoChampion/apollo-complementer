from __future__ import annotations

from typing import Any, Protocol


class ApolloClient(Protocol):
    def search_people(
        self,
        *,
        q_keywords: str | None = None,
        organization_ids: list[str] | None = None,
        person_titles: list[str] | None = None,
        person_locations: list[str] | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict[str, Any]: ...

    def search_companies(
        self,
        *,
        q_organization_name: str | None = None,
        organization_locations: list[str] | None = None,
        organization_num_employees_range: list[int] | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict[str, Any]: ...

    def enrich_organization(
        self,
        *,
        domain: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]: ...

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
    ) -> dict[str, Any]: ...
