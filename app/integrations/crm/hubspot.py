from typing import Any

import httpx

from app.core.config import get_settings
from app.integrations.crm.base import CompanyRecord, ContactRecord, CRMResult, TaskRecord

HUBSPOT_API_BASE = "https://api.hubapi.com"


class HubSpotAdapter:
    def __init__(
        self,
        *,
        token: str | None = None,
        client: httpx.Client | None = None,
        base_url: str = HUBSPOT_API_BASE,
    ) -> None:
        self.token = token or get_settings().hubspot_private_app_token
        if not self.token:
            raise ValueError("HubSpot private app token is not configured.")
        self.client = client or httpx.Client(timeout=20)
        self.base_url = base_url.rstrip("/")

    def upsert_company(self, company: CompanyRecord) -> CRMResult:
        search = self._search_object(
            "companies",
            property_name="domain",
            value=_domain_from_website(company.website) or company.name,
        )
        properties = {
            "name": company.name,
            "domain": _domain_from_website(company.website),
            "country": company.country,
            "industry": company.industry,
        }
        if search:
            return self._patch_object("companies", search, properties)
        return self._create_object("companies", properties)

    def upsert_contact(self, contact: ContactRecord) -> CRMResult:
        search = self._search_object("contacts", property_name="email", value=contact.email)
        properties = {
            "email": contact.email,
            "firstname": contact.first_name,
            "lastname": contact.last_name,
            "jobtitle": contact.job_title,
            "company": contact.company_name,
        }
        if search:
            return self._patch_object("contacts", search, properties)
        return self._create_object("contacts", properties)

    def create_note(self, contact_id: str, note: str) -> CRMResult:
        payload = {
            "properties": {
                "hs_note_body": note,
            },
            "associations": [
                {
                    "to": {"id": contact_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 202,
                        }
                    ],
                }
            ],
        }
        response = self._request("POST", "/crm/v3/objects/notes", json=payload)
        return _result_from_response(response)

    def create_task(self, contact_id: str, task: TaskRecord) -> CRMResult:
        payload = {
            "properties": {
                "hs_task_subject": task.title,
                "hs_task_body": task.body or "",
                "hs_task_status": "NOT_STARTED",
            },
            "associations": [
                {
                    "to": {"id": contact_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 204,
                        }
                    ],
                }
            ],
        }
        response = self._request("POST", "/crm/v3/objects/tasks", json=payload)
        return _result_from_response(response)

    def _search_object(self, object_type: str, *, property_name: str, value: str) -> str | None:
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": property_name,
                            "operator": "EQ",
                            "value": value,
                        }
                    ]
                }
            ],
            "limit": 1,
        }
        response = self._request("POST", f"/crm/v3/objects/{object_type}/search", json=payload)
        results = response.get("results", [])
        return results[0]["id"] if results else None

    def _create_object(self, object_type: str, properties: dict[str, Any]) -> CRMResult:
        response = self._request(
            "POST",
            f"/crm/v3/objects/{object_type}",
            json={"properties": _clean_properties(properties)},
        )
        return _result_from_response(response)

    def _patch_object(
        self,
        object_type: str,
        external_id: str,
        properties: dict[str, Any],
    ) -> CRMResult:
        response = self._request(
            "PATCH",
            f"/crm/v3/objects/{object_type}/{external_id}",
            json={"properties": _clean_properties(properties)},
        )
        return _result_from_response(response)

    def _request(self, method: str, path: str, *, json: dict[str, Any]) -> dict[str, Any]:
        response = self.client.request(
            method,
            f"{self.base_url}{path}",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            json=json,
        )
        response.raise_for_status()
        return response.json()


def _clean_properties(properties: dict[str, Any]) -> dict[str, str]:
    return {key: str(value) for key, value in properties.items() if value not in (None, "")}


def _domain_from_website(website: str | None) -> str | None:
    if not website:
        return None
    domain = website.replace("https://", "").replace("http://", "").split("/")[0]
    return domain.removeprefix("www.")


def _result_from_response(response: dict[str, Any]) -> CRMResult:
    external_id = str(response["id"])
    return CRMResult(
        external_id=external_id,
        url=f"https://app.hubspot.com/contacts/0/record/0-1/{external_id}",
        raw=response,
    )
