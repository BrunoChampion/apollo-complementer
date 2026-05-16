import shutil
from pathlib import Path

from app.domain.enrichment import EnrichmentResult, EnrichmentStatus, RecommendedAction
from app.integrations.sheets.constants import (
    EMAIL_DRAFTS_TAB,
    ENRICHMENT_TAB,
    LEADS_HEADERS,
    LEADS_TAB,
)
from app.integrations.sheets.fake_multi_tab import MultiTabFakeSheetClient
from app.services.lead_enrich_and_draft_service import LeadEnrichAndDraftService

TEMP_DIR = Path("C:/Users/bruno/AppData/Local/Temp/opencode/enrichment_draft_sheet")


def setup_function() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def teardown_function() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)


def test_draft_leads_appends_generated_email_to_email_drafts_tab() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR)
    enrichment = EnrichmentResult(
        enrichment_id="enr-1",
        lead_id="lead-1",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="Acme",
        b2b_fit=True,
        operational_pain_hypothesis=(
            "el conocimiento queda repartido entre soporte, onboarding y documentacion"
        ),
        confidence_score=90,
        recommended_action=RecommendedAction.DRAFT,
        evidence_items=[
            {
                "claim": (
                    "Acme tiene flujos B2B de soporte, onboarding, implementacion "
                    "y documentacion para clientes"
                ),
                "source_type": "manual_context",
                "confidence": 90,
                "used_in_message": True,
            }
        ],
    )
    client.append_row(
        tab_name=LEADS_TAB,
        headers=LEADS_HEADERS,
        values={
            "lead_id": "lead-1",
            "company_name": "Acme",
            "company_website": "https://acme.example",
            "company_linkedin_url": "https://www.linkedin.com/company/acme/",
            "prospect_name": "Ana Perez",
            "prospect_title": "COO",
            "prospect_linkedin_url": "https://www.linkedin.com/in/ana-perez/",
            "prospect_email": "ana@acme.example",
            "country": "Mexico",
            "company_size": "50",
            "industry": "SaaS B2B",
            "manual_company_linkedin_text": (
                "Acme es una empresa B2B con soporte, onboarding, implementacion "
                "y documentacion para clientes."
            ),
            "manual_person_linkedin_text": "Ana Perez es COO en Acme.",
            "status": "enriched",
            "enrichment_result": enrichment.model_dump(mode="json"),
        },
    )

    results = LeadEnrichAndDraftService(client).draft_leads(
        lead_ids=["lead-1"],
        run_id="run-draft-1",
    )

    assert len(results) == 1
    assert results[0]["email_draft"]

    lead_rows = client.read_rows(tab_name=LEADS_TAB)
    assert lead_rows[0].values["email_draft"]

    email_draft_rows = client.read_rows(tab_name=EMAIL_DRAFTS_TAB)
    assert len(email_draft_rows) == 1
    assert email_draft_rows[0].values["run_id"] == "run-draft-1"
    assert email_draft_rows[0].values["lead_id"] == "lead-1"
    assert email_draft_rows[0].values["email_subject"]
    assert email_draft_rows[0].values["email_draft"]
    assert email_draft_rows[0].values["enrichment_id"] == "enr-1"

    assert client.read_rows(tab_name=ENRICHMENT_TAB) == []
