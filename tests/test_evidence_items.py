from app.db.repositories import RunRepository
from app.domain.leads import LeadRow
from app.services.evidence import evidence_to_json, extract_evidence_items
from tests.db_utils import build_test_session


def test_extracts_evidence_from_manual_context() -> None:
    lead = LeadRow.model_validate(
        {
            "lead_id": "lead_001",
            "company_name": "Andes ERP Partners",
            "source_url": "https://example.com/source",
            "manual_context": "Consultora B2B de implementacion ERP.",
        }
    )

    items = extract_evidence_items(lead, "Consultora B2B de implementacion ERP.")

    assert len(items) == 1
    assert items[0].source_type == "manual_context"
    assert items[0].used_in_message is True
    assert evidence_to_json(items)[0]["confidence"] == "medium"


def test_persists_evidence_item_for_lead_run() -> None:
    session = next(build_test_session())
    repository = RunRepository(session)
    run = repository.create_run(source="fake_sheet")
    lead_run = repository.create_lead_run(
        run_id=run.id,
        lead_id="lead_001",
        row_number=2,
        action="research_and_draft",
        status="completed",
        finished=True,
    )

    evidence = repository.create_evidence_item(
        lead_run_id=lead_run.id,
        lead_id="lead_001",
        claim="Consultora B2B de implementacion ERP.",
        source_type="manual_context",
        source_url="https://example.com/source",
        confidence="medium",
        used_in_message=True,
    )

    items = repository.list_evidence_items(lead_run.id)
    assert evidence.id == items[0].id
    assert items[0].used_in_message is True
