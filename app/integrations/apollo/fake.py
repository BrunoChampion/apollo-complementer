from __future__ import annotations

from typing import Any


class FakeApolloClient:
    """Deterministic fake Apollo client for tests and local development."""

    def __init__(self, min_candidate_score: int = 60) -> None:
        self.min_candidate_score = min_candidate_score

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
        return {
            "people": [
                {
                    "id": f"person_{page}_{i}",
                    "first_name": "Juan",
                    "last_name": "Perez",
                    "name": "Juan Perez",
                    "title": (person_titles or ["CEO"])[0] if person_titles else "CEO",
                    "email": f"juan{i}@example.com",
                    "organization": {
                        "id": f"org_{i}",
                        "name": "Acme Corp",
                        "website_url": "https://acme.com",
                    },
                    "phone_numbers": [],
                    "linkedin_url": f"https://linkedin.com/in/juanperez{i}",
                }
                for i in range(min(per_page, 3))
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_entries": 3,
                "total_pages": 1,
            },
        }

    def search_companies(
        self,
        *,
        q_organization_name: str | None = None,
        organization_locations: list[str] | None = None,
        organization_num_employees_range: list[int] | None = None,
        page: int = 1,
        per_page: int = 25,
    ) -> dict[str, Any]:
        return {
            "organizations": [
                {
                    "id": f"org_{page}_{i}",
                    "name": q_organization_name or "Acme Corp",
                    "website_url": "https://acme.com",
                    "linkedin_url": "https://linkedin.com/company/acme",
                    "primary_phone": {"number": "+541123456789"},
                    "estimated_num_employees": 50,
                    "industry": "Software",
                    "location": {
                        "address_line_1": "Av Example 123",
                        "city": "Buenos Aires",
                        "country": "Argentina",
                    },
                }
                for i in range(min(per_page, 2))
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_entries": 2,
                "total_pages": 1,
            },
        }

    def enrich_organization(
        self,
        *,
        domain: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        return {
            "organization": {
                "id": "org_enriched_1",
                "name": name or "Acme Corp",
                "website_url": domain or "https://acme.com",
                "linkedin_url": "https://linkedin.com/company/acme",
                "primary_phone": {"number": "+541123456789"},
                "estimated_num_employees": 50,
                "industry": "Software",
                "location": {
                    "address_line_1": "Av Example 123",
                    "city": "Buenos Aires",
                    "country": "Argentina",
                },
            },
        }

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
        person_name = name or "Juan Perez"
        return {
            "person": {
                "id": id or "person_enriched_1",
                "first_name": person_name.split(" ")[0],
                "last_name": person_name.split(" ")[-1] if " " in person_name else None,
                "name": person_name,
                "title": "CEO",
                "email": email or "juan@example.com",
                "organization": {
                    "id": "org_enriched_1",
                    "name": "Acme Corp",
                    "website_url": f"https://{domain}" if domain else "https://acme.com",
                },
                "phone_numbers": [],
                "linkedin_url": linkedin_url or "https://linkedin.com/in/juanperez",
            },
        }
