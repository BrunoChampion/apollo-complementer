import json

import httpx

from app.integrations.crm.base import CompanyRecord, ContactRecord, TaskRecord
from app.integrations.crm.hubspot import HubSpotAdapter


def test_hubspot_upsert_company_creates_when_not_found() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/search"):
            return httpx.Response(200, json={"results": []})
        return httpx.Response(200, json={"id": "company_123", "properties": {}})

    adapter = HubSpotAdapter(
        token="token",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = adapter.upsert_company(
        CompanyRecord(
            name="Andes ERP Partners",
            website="https://www.andeserp.example.com/path",
            country="Peru",
            industry="ERP",
        )
    )

    create_body = json.loads(calls[1].content)
    assert result.external_id == "company_123"
    assert calls[1].method == "POST"
    assert calls[1].url.path == "/crm/v3/objects/companies"
    assert create_body["properties"]["domain"] == "andeserp.example.com"


def test_hubspot_upsert_contact_patches_when_found() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/search"):
            return httpx.Response(200, json={"results": [{"id": "contact_123"}]})
        return httpx.Response(200, json={"id": "contact_123", "properties": {}})

    adapter = HubSpotAdapter(
        token="token",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = adapter.upsert_contact(
        ContactRecord(
            email="camila@example.com",
            first_name="Camila",
            last_name="Rojas",
            job_title="Founder",
            company_name="Andes ERP Partners",
        )
    )

    patch_body = json.loads(calls[1].content)
    assert result.external_id == "contact_123"
    assert calls[1].method == "PATCH"
    assert calls[1].url.path == "/crm/v3/objects/contacts/contact_123"
    assert patch_body["properties"]["email"] == "camila@example.com"


def test_hubspot_creates_note_and_task_associated_to_contact() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"id": f"obj_{len(calls)}", "properties": {}})

    adapter = HubSpotAdapter(
        token="token",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    note = adapter.create_note("contact_123", "Research summary")
    task = adapter.create_task(
        "contact_123",
        TaskRecord(title="Review AI-generated draft", body="Open Gmail draft."),
    )

    note_body = json.loads(calls[0].content)
    task_body = json.loads(calls[1].content)
    assert note.external_id == "obj_1"
    assert task.external_id == "obj_2"
    assert calls[0].url.path == "/crm/v3/objects/notes"
    assert calls[1].url.path == "/crm/v3/objects/tasks"
    assert note_body["associations"][0]["to"]["id"] == "contact_123"
    assert task_body["properties"]["hs_task_subject"] == "Review AI-generated draft"
