import shutil
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from app.domain.enrichment import (
    EnrichmentStatus,
    EvidenceItem,
    EvidenceSourceType,
    RecommendedAction,
)
from app.integrations.sheets.constants import ENRICHMENT_TAB, LEADS_HEADERS, LEADS_TAB
from app.integrations.sheets.fake_multi_tab import MultiTabFakeSheetClient
from app.services.lead_enrich_and_draft_service import LeadEnrichAndDraftService

TEMP_DIR = Path(
    "C:/Users/bruno/AppData/Local/Temp/opencode/lead_enrich_and_draft_sheet_test"
)


class FakeEnrichAndDraft:
    def enrich_and_draft(self, lead: Any, run_id: str) -> dict[str, Any]:
        return {
            "lead_id": lead.lead_id,
            "status": "needs_manual_research",
            "agent_note": "Enrichment captured; draft withheld.",
            "enrichment_result": {
                "enrichment_id": "enrich_001",
                "run_id": run_id,
                "lead_id": lead.lead_id,
                "company_name": lead.company_name,
                "company_domain": lead.company_domain,
                "prospect_linkedin_url": lead.prospect_linkedin_url,
                "country": lead.country,
                "industry": lead.industry,
                "company_size": lead.company_size,
                "enrichment_status": EnrichmentStatus.ENRICHED.value,
                "company_summary": "SaaS company in Argentina.",
                "confidence_score": 72,
                "recommended_action": RecommendedAction.NEEDS_MANUAL_RESEARCH.value,
                "evidence_items": [
                    EvidenceItem(
                        claim="Uses HubSpot",
                        source_type=EvidenceSourceType.WEBSITE,
                        source_url="https://acme.com",
                        quote_or_summary="HubSpot script found on the website.",
                    ).model_dump(mode="json")
                ],
            },
        }


def setup_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def teardown_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)


def test_enrich_and_draft_appends_enrichment_tab_row() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "case_1")
    client.append_row(
        tab_name=LEADS_TAB,
        headers=LEADS_HEADERS,
        values={
            "lead_id": "lead_001",
            "company_name": "Acme",
            "company_domain": "acme.com",
            "prospect_linkedin_url": "https://linkedin.com/in/ana",
            "country": "Argentina",
            "industry": "software",
            "company_size": "51-200",
            "action": "enrich_and_draft",
            "status": "new",
        },
    )

    service = LeadEnrichAndDraftService(client)
    service.service = FakeEnrichAndDraft()

    results = service.enrich_and_draft_leads(run_id="run_001")
    enrichment_rows = client.read_rows(tab_name=ENRICHMENT_TAB)

    assert len(results) == 1
    assert len(enrichment_rows) == 1
    assert enrichment_rows[0].values["lead_id"] == "lead_001"
    assert enrichment_rows[0].values["company_domain"] == "acme.com"
    assert enrichment_rows[0].values["prospect_linkedin_url"] == (
        "https://linkedin.com/in/ana"
    )
    assert enrichment_rows[0].values["evidence_summary"] == (
        "HubSpot script found on the website."
    )
    assert enrichment_rows[0].values["evidence_urls"] == "https://acme.com"


def test_sync_enrichment_results_from_leads_backfills_enrichment_tab() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "case_2")
    client.append_row(
        tab_name=LEADS_TAB,
        headers=LEADS_HEADERS,
        values={
            "lead_id": "lead_002",
            "company_name": "Beta",
            "action": "enrich_and_draft",
            "status": "needs_manual_research",
            "enrichment_result": {
                "enrichment_id": "enrich_002",
                "lead_id": "lead_002",
                "company_name": "Beta",
                "company_domain": "beta.com",
                "enrichment_status": EnrichmentStatus.ENRICHED.value,
                "company_summary": "Fintech in Uruguay.",
                "recommended_action": (
                    RecommendedAction.NEEDS_MANUAL_RESEARCH.value
                ),
                "evidence_items": [
                    {
                        "claim": "Serves merchants",
                        "source_type": EvidenceSourceType.WEBSITE.value,
                        "source_url": "https://beta.com",
                        "quote_or_summary": "Merchant checkout product.",
                    }
                ],
            },
        },
    )

    service = LeadEnrichAndDraftService(client)
    service.service = Mock()

    results = service.sync_enrichment_results_from_leads(run_id="manual_sync")
    enrichment_rows = client.read_rows(tab_name=ENRICHMENT_TAB)

    service.service.enrich_and_draft.assert_not_called()
    assert len(results) == 1
    assert enrichment_rows[0].values["lead_id"] == "lead_002"
    assert enrichment_rows[0].values["run_id"] == "manual_sync"
    assert enrichment_rows[0].values["evidence_summary"] == "Merchant checkout product."


def test_enrich_and_draft_backfills_existing_result_before_skipping_status() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "case_4")
    client.append_row(
        tab_name=LEADS_TAB,
        headers=LEADS_HEADERS,
        values={
            "lead_id": "lead_004",
            "company_name": "Delta",
            "action": "enrich_and_draft",
            "status": "needs_manual_research",
            "enrichment_result": {
                "enrichment_id": "enrich_004",
                "lead_id": "lead_004",
                "company_name": "Delta",
                "enrichment_status": EnrichmentStatus.ENRICHED.value,
                "company_summary": "Ops platform in Chile.",
                "recommended_action": (
                    RecommendedAction.NEEDS_MANUAL_RESEARCH.value
                ),
            },
        },
    )

    service = LeadEnrichAndDraftService(client)
    service.service = Mock()

    results = service.enrich_and_draft_leads(run_id="manual")
    enrichment_rows = client.read_rows(tab_name=ENRICHMENT_TAB)

    service.service.enrich_and_draft.assert_not_called()
    assert results == []
    assert len(enrichment_rows) == 1
    assert enrichment_rows[0].values["lead_id"] == "lead_004"


def test_enrich_and_draft_force_reprocesses_terminal_status() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "case_5")
    client.append_row(
        tab_name=LEADS_TAB,
        headers=LEADS_HEADERS,
        values={
            "lead_id": "lead_005",
            "company_name": "Epsilon",
            "company_domain": "epsilon.com",
            "country": "Chile",
            "action": "enrich_and_draft",
            "status": "needs_manual_research",
            "enrichment_result": {
                "enrichment_id": "old_enrich_005",
                "lead_id": "lead_005",
                "company_name": "Epsilon",
                "enrichment_status": EnrichmentStatus.ENRICHED.value,
                "recommended_action": RecommendedAction.NEEDS_MANUAL_RESEARCH.value,
            },
        },
    )

    service = LeadEnrichAndDraftService(client)
    service.service = FakeEnrichAndDraft()

    results = service.enrich_and_draft_leads(
        lead_ids=["lead_005"],
        run_id="run_force",
        force=True,
    )

    assert len(results) == 1
    assert results[0]["enrichment_result"]["enrichment_id"] == "enrich_001"


def test_enrich_and_draft_retries_terminal_status_without_enrichment_result() -> None:
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "case_3")
    client.append_row(
        tab_name=LEADS_TAB,
        headers=LEADS_HEADERS,
        values={
            "lead_id": "lead_003",
            "company_name": "Gamma",
            "company_domain": "gamma.com",
            "country": "Chile",
            "action": "enrich_and_draft",
            "status": "needs_manual_research",
            "enrichment_result": "",
        },
    )

    service = LeadEnrichAndDraftService(client)
    service.service = FakeEnrichAndDraft()

    results = service.enrich_and_draft_leads(run_id="run_retry")
    enrichment_rows = client.read_rows(tab_name=ENRICHMENT_TAB)

    assert len(results) == 1
    assert len(enrichment_rows) == 1
    assert enrichment_rows[0].values["lead_id"] == "lead_003"
