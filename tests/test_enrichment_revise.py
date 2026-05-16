import json
from pathlib import Path
from uuid import uuid4

from app.domain.enrichment import EnrichmentResult, EvidenceItem
from app.integrations.sheets.constants import LEADS_HEADERS, LEADS_TAB
from app.integrations.sheets.fake_multi_tab import MultiTabFakeSheetClient
from app.services.enrich_and_draft_service import EnrichAndDraftService
from app.services.lead_enrich_and_draft_service import LeadEnrichAndDraftService


def _enrichment_json() -> str:
    result = EnrichmentResult(
        enrichment_id="enr-1",
        company_name="Acme",
        company_website="https://acme.com",
        confidence_score=80,
        recommended_action="draft",
        evidence_items=[
            EvidenceItem(
                claim="Acme uses HubSpot on its website",
                source_type="website",
                source_url="https://acme.com",
                quote_or_summary="hubspot.net script detected",
                confidence=70,
                used_in_message=True,
            )
        ],
    )
    return json.dumps(result.model_dump(mode="json"))


def test_revise_uses_existing_enrichment() -> None:
    service = EnrichAndDraftService()
    lead = {
        "lead_id": "lead-1",
        "company_name": "Acme",
        "country": "Mexico",
        "action": "revise",
        "status": "needs_revision",
        "email_draft": (
            "Hola Ana, vi que Acme uses HubSpot on its website. Tiene sentido conversar?"
        ),
        "revision_instruction": "Hazlo mas directo y conserva HubSpot.",
        "enrichment_result": _enrichment_json(),
    }

    result = service.revise_enriched_draft(service_lead(lead), run_id="run-1")

    assert result["status"] in {"revised", "needs_revision"}
    assert result["enrichment_result"]["company_name"] == "Acme"
    assert "Ajuste aplicado" in (result["revised_draft"] or result["email_draft"])


def test_revise_reads_revision_instruction_from_sheet() -> None:
    sheet_dir = Path("tests") / f"tmp_revise_sheet_{uuid4().hex}"
    client = MultiTabFakeSheetClient(sheet_dir)
    client.append_row(
        tab_name=LEADS_TAB,
        headers=LEADS_HEADERS,
        values={
            "lead_id": "lead-1",
            "company_name": "Acme",
            "country": "Mexico",
            "action": "revise",
            "status": "needs_revision",
            "email_draft": (
                "Hola Ana, vi que Acme uses HubSpot on its website. "
                "Tiene sentido conversar?"
            ),
            "revision_instruction": "Hazlo mas directo y conserva HubSpot.",
            "enrichment_result": _enrichment_json(),
        },
    )

    results = LeadEnrichAndDraftService(client).revise_enriched_drafts(run_id="run-1")
    rows = client.read_rows(tab_name=LEADS_TAB)

    assert len(results) == 1
    assert rows[0].values["revision_count"] == "1"
    assert rows[0].values["last_processed_revision_hash"]


def test_revise_requires_existing_enrichment() -> None:
    service = EnrichAndDraftService()
    lead = service_lead(
        {
            "lead_id": "lead-2",
            "company_name": "Acme",
            "country": "Mexico",
            "action": "revise",
            "email_draft": "Hola Ana, draft previo.",
            "revision_instruction": "Hazlo mas corto.",
        }
    )

    result = service.revise_enriched_draft(lead, run_id="run-1")

    assert result["status"] == "error"
    assert "enrichment_result is required" in result["agent_note"]


def service_lead(values: dict):
    from app.domain.leads import LeadRow

    return LeadRow.model_validate(values)
