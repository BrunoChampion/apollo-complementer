import shutil
from pathlib import Path

from app.domain.enrichment import EnrichmentResult, EnrichmentStatus, RecommendedAction
from app.integrations.sheets.constants import (
    EMAIL_DRAFTS_TAB,
    ENRICHMENT_HEADERS,
    ENRICHMENT_TAB,
    LEADS_HEADERS,
    LEADS_TAB,
)
from app.integrations.sheets.fake_multi_tab import MultiTabFakeSheetClient
from app.services.lead_enrich_and_draft_service import LeadEnrichAndDraftService

TEMP_DIR = Path("C:/Users/bruno/AppData/Local/Temp/opencode/enrichment_draft_sheet")


class FakeBlockedDraftService:
    def draft_from_existing_enrichment(self, lead, run_id: str) -> dict:
        return {
            "lead_id": lead.lead_id,
            "status": "needs_manual_research",
            "agent_note": "Draft blocked before generation. company is above 200 employees.",
            "quality_issues": ["company is above 200 employees and needs a strong exception"],
            "enrichment_result": lead.enrichment_result,
        }


class FakeExactEnrichmentDraftService:
    def draft_from_existing_enrichment(self, lead, run_id: str) -> dict:
        enrichment = lead.enrichment_result
        assert enrichment["enrichment_id"] == "enr-selected"
        assert enrichment["company_name"] == "FreshCo"
        assert "fresh support signal" in enrichment["evidence_items"][0]["claim"]
        return {
            "lead_id": lead.lead_id,
            "status": "drafted",
            "agent_note": "Draft generated from exact enrichment row.",
            "email_subject": "Hipotesis para FreshCo",
            "email_draft": "Hola Ana,\n\nVi que FreshCo tiene soporte B2B.\n\nTiene sentido?",
            "quality_score": 95,
            "enrichment_result": enrichment,
            "message_brief": {"selected_signal_es": "tiene soporte B2B"},
            "raw_selected_evidence_claim": enrichment["evidence_items"][0]["claim"],
            "supporting_evidence_ids": ["ev_1"],
            "signal_candidates": [{"evidence_id": "ev_1", "score": 90}],
            "draft_contract_version": "nyvex-draft-contract-v2",
        }


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


def test_draft_leads_appends_audit_row_when_draft_is_blocked_before_generation() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR)
    enrichment = EnrichmentResult(
        enrichment_id="enr-blocked",
        lead_id="lead-blocked",
        enrichment_status=EnrichmentStatus.NEEDS_REVIEW,
        company_name="LargeCo",
        b2b_fit=True,
        operational_pain_hypothesis="possible support and implementation complexity",
        confidence_score=82,
        recommended_action=RecommendedAction.NEEDS_MANUAL_RESEARCH,
        evidence_items=[],
    )
    client.append_row(
        tab_name=LEADS_TAB,
        headers=LEADS_HEADERS,
        values={
            "lead_id": "lead-blocked",
            "company_name": "LargeCo",
            "prospect_name": "Luis Gomez",
            "prospect_title": "COO",
            "prospect_email": "luis@largeco.example",
            "country": "Argentina",
            "company_size": "500",
            "status": "needs_manual_research",
            "enrichment_result": enrichment.model_dump(mode="json"),
        },
    )

    service = LeadEnrichAndDraftService(client)
    service.service = FakeBlockedDraftService()
    results = service.draft_leads(lead_ids=["lead-blocked"], run_id="run-blocked")

    assert len(results) == 1
    assert not results[0].get("email_draft")

    email_draft_rows = client.read_rows(tab_name=EMAIL_DRAFTS_TAB)
    assert len(email_draft_rows) == 1
    audit_row = email_draft_rows[0].values
    assert audit_row["run_id"] == "run-blocked"
    assert audit_row["lead_id"] == "lead-blocked"
    assert audit_row["email_draft"] == ""
    assert audit_row["draft_status"] == "blocked_before_draft"
    assert "above 200 employees" in audit_row["agent_note"]
    assert audit_row["enrichment_id"] == "enr-blocked"


def test_enrichment_writer_stores_full_result_json_for_drafting() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR)
    enrichment = EnrichmentResult(
        enrichment_id="enr-json",
        lead_id="lead-json",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="JsonCo",
        recommended_action=RecommendedAction.DRAFT,
        evidence_items=[
            {
                "claim": "JsonCo has support documentation",
                "source_type": "manual_context",
                "confidence": 90,
            }
        ],
    )

    service = LeadEnrichAndDraftService(client)
    service.sheet_writer.append(enrichment)

    row = client.read_rows(tab_name=ENRICHMENT_TAB)[0].values
    assert row["enrichment_result_json"]
    assert "JsonCo has support documentation" in row["enrichment_result_json"]


def test_draft_selected_enrichment_id_uses_exact_enrichment_json_not_stale_leads() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR)
    stale_enrichment = EnrichmentResult(
        enrichment_id="enr-stale",
        lead_id="lead-selected",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="StaleCo",
        recommended_action=RecommendedAction.DRAFT,
        evidence_items=[
            {
                "claim": "stale retail signal from another company",
                "source_type": "manual_context",
                "confidence": 90,
            }
        ],
    )
    selected_enrichment = EnrichmentResult(
        enrichment_id="enr-selected",
        lead_id="lead-selected",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_name="FreshCo",
        recommended_action=RecommendedAction.DRAFT,
        confidence_score=95,
        evidence_items=[
            {
                "claim": "fresh support signal for B2B customers",
                "source_type": "manual_context",
                "confidence": 90,
            }
        ],
    )
    client.append_row(
        tab_name=LEADS_TAB,
        headers=LEADS_HEADERS,
        values={
            "lead_id": "lead-selected",
            "company_name": "FreshCo",
            "company_linkedin_url": "https://www.linkedin.com/company/freshco/",
            "prospect_name": "Ana Perez",
            "prospect_title": "COO",
            "prospect_linkedin_url": "https://www.linkedin.com/in/ana-perez/",
            "prospect_email": "ana@freshco.example",
            "country": "Mexico",
            "company_size": "50",
            "manual_company_linkedin_text": "FreshCo es una empresa B2B con soporte.",
            "manual_person_linkedin_text": "Ana Perez es COO en FreshCo.",
            "status": "enriched",
            "enrichment_result": stale_enrichment.model_dump(mode="json"),
        },
    )
    client.append_row(
        tab_name=ENRICHMENT_TAB,
        headers=ENRICHMENT_HEADERS,
        values={
            **selected_enrichment.model_dump(mode="json"),
            "enrichment_result_json": selected_enrichment.model_dump(mode="json"),
        },
    )
    service = LeadEnrichAndDraftService(client)
    service.service = FakeExactEnrichmentDraftService()

    results = service.draft_leads(
        enrichment_ids=["enr-selected"],
        run_id="run-selected",
    )

    assert len(results) == 1
    assert results[0]["source_enrichment_id"] == "enr-selected"
    email_draft = client.read_rows(tab_name=EMAIL_DRAFTS_TAB)[0].values
    assert email_draft["source_enrichment_id"] == "enr-selected"
    assert email_draft["source_tab"] == ENRICHMENT_TAB
    assert "tiene soporte B2B" in email_draft["message_brief"]


def test_draft_selected_enrichment_without_full_json_is_audited_not_drafted() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR)
    client.append_row(
        tab_name=LEADS_TAB,
        headers=LEADS_HEADERS,
        values={
            "lead_id": "lead-old",
            "company_name": "OldCo",
            "company_linkedin_url": "https://www.linkedin.com/company/oldco/",
            "prospect_name": "Luis Gomez",
            "prospect_linkedin_url": "https://www.linkedin.com/in/luis-gomez/",
            "country": "Chile",
            "manual_company_linkedin_text": "OldCo es una empresa B2B.",
            "manual_person_linkedin_text": "Luis Gomez trabaja en OldCo.",
            "status": "enriched",
        },
    )
    client.append_row(
        tab_name=ENRICHMENT_TAB,
        headers=ENRICHMENT_HEADERS,
        values={
            "enrichment_id": "enr-old",
            "lead_id": "lead-old",
            "company_name": "OldCo",
            "enrichment_status": "enriched",
            "recommended_action": "draft",
        },
    )

    results = LeadEnrichAndDraftService(client).draft_leads(
        enrichment_ids=["enr-old"],
        run_id="run-old",
    )

    assert results[0]["status"] == "needs_manual_research"
    draft_row = client.read_rows(tab_name=EMAIL_DRAFTS_TAB)[0].values
    assert draft_row["draft_status"] == "blocked_before_draft"
    assert draft_row["source_enrichment_id"] == "enr-old"
    assert "missing enrichment_result_json" in draft_row["agent_note"]
