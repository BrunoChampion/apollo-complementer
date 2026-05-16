import shutil
from pathlib import Path

from app.db.models import EnrichmentRun
from app.db.repositories import EnrichmentRepository
from app.domain.enrichment import (
    EnrichmentResult,
    EnrichmentStatus,
    EvidenceItem,
    EvidenceSourceType,
    RecommendedAction,
)
from app.integrations.sheets.constants import ENRICHMENT_TAB
from app.integrations.sheets.fake_multi_tab import MultiTabFakeSheetClient
from app.services.enrichment_persistence_service import EnrichmentPersistenceService
from tests.db_utils import build_test_session

TEMP_DIR = Path("C:/Users/bruno/AppData/Local/Temp/opencode/enrichment_persistence_test")


def setup_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def teardown_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)


def test_create_enrichment_run_in_db() -> None:
    session = next(build_test_session())
    repository = EnrichmentRepository(session)
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "test_1")
    service = EnrichmentPersistenceService(repository, client)

    result = EnrichmentResult(
        enrichment_id="enrich_001",
        run_id="run_001",
        lead_id="lead_001",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_summary="AI startup in Mexico",
        b2b_fit=True,
        operational_pain_hypothesis="Manual support scaling",
        possible_ai_use_case="Agentic RAG for support",
        personalization_angle="Hiring 5 support reps",
        trigger_summary="Recent job postings",
        confidence_score=85,
        recommended_action=RecommendedAction.DRAFT,
    )

    enrichment = service.persist(result)

    assert isinstance(enrichment, EnrichmentRun)
    assert enrichment.id is not None
    assert enrichment.lead_id == "lead_001"
    assert enrichment.status == "enriched"
    assert enrichment.confidence_score == 85
    assert enrichment.recommended_action == "draft"


def test_add_evidence_items_in_db() -> None:
    session = next(build_test_session())
    repository = EnrichmentRepository(session)
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "test_2")
    service = EnrichmentPersistenceService(repository, client)

    result = EnrichmentResult(
        enrichment_id="enrich_002",
        lead_id="lead_002",
        enrichment_status=EnrichmentStatus.ENRICHED,
        evidence_items=[
            EvidenceItem(
                claim="Hiring 5 support reps",
                source_type=EvidenceSourceType.CAREERS,
                source_url="https://example.com/careers",
                confidence=90,
            ),
            EvidenceItem(
                claim="Recently raised Series A",
                source_type=EvidenceSourceType.BLOG,
                confidence=75,
            ),
        ],
        recommended_action=RecommendedAction.DRAFT,
    )

    enrichment = service.persist(result)
    items = repository.list_evidence_items(enrichment.id)

    assert len(items) == 2
    assert items[0].claim == "Hiring 5 support reps"
    assert items[0].source_type == "careers"
    assert items[1].confidence == 75


def test_serialize_to_sheet() -> None:
    session = next(build_test_session())
    repository = EnrichmentRepository(session)
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "test_3")
    service = EnrichmentPersistenceService(repository, client)

    result = EnrichmentResult(
        enrichment_id="enrich_003",
        lead_id="lead_003",
        company_domain="acme.com",
        company_linkedin_url="https://linkedin.com/company/acme",
        prospect_linkedin_url="https://linkedin.com/in/ana",
        country="Argentina",
        company_size="80",
        enrichment_status=EnrichmentStatus.ENRICHED,
        company_summary="SaaS company in Argentina",
        confidence_score=70,
        recommended_action=RecommendedAction.NEEDS_MANUAL_RESEARCH,
        evidence_items=[
            EvidenceItem(
                claim="Uses HubSpot",
                source_type=EvidenceSourceType.WEBSITE,
                source_url="https://acme.com",
                quote_or_summary="HubSpot script detected on homepage.",
                confidence=70,
            )
        ],
    )

    service.persist(result)
    sheet_rows = client.read_rows(tab_name=ENRICHMENT_TAB)

    assert len(sheet_rows) == 1
    assert sheet_rows[0].values["enrichment_id"] == "enrich_003"
    assert sheet_rows[0].values["lead_id"] == "lead_003"
    assert sheet_rows[0].values["company_domain"] == "acme.com"
    assert sheet_rows[0].values["country"] == "Argentina"
    assert sheet_rows[0].values["evidence_summary"] == "HubSpot script detected on homepage."
    assert sheet_rows[0].values["evidence_urls"] == "https://acme.com"
    assert sheet_rows[0].values["confidence_score"] == "70"
    assert sheet_rows[0].values["recommended_action"] == "needs_manual_research"


def test_persist_failed_enrichment() -> None:
    session = next(build_test_session())
    repository = EnrichmentRepository(session)
    client = MultiTabFakeSheetClient(directory=TEMP_DIR / "test_4")
    service = EnrichmentPersistenceService(repository, client)

    result = EnrichmentResult(
        enrichment_id="enrich_004",
        lead_id="lead_004",
        enrichment_status=EnrichmentStatus.FAILED,
        error_message="Website unreachable",
        recommended_action=RecommendedAction.DISCARD,
    )

    enrichment = service.persist(result)
    assert enrichment.status == "failed"
    assert enrichment.error_message == "Website unreachable"

    sheet_rows = client.read_rows(tab_name=ENRICHMENT_TAB)
    assert len(sheet_rows) == 1
    assert sheet_rows[0].values["error_message"] == "Website unreachable"
