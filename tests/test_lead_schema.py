import csv
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.leads import LeadAction, LeadRow, LeadStatus


def test_lead_row_validates_required_fields() -> None:
    lead = LeadRow.model_validate(
        {
            "lead_id": "lead_001",
            "company_name": "Andes ERP Partners",
            "action": "research_and_draft",
            "status": "new",
        }
    )

    assert lead.lead_id == "lead_001"
    assert lead.action is LeadAction.RESEARCH_AND_DRAFT
    assert lead.status is LeadStatus.NEW


def test_invalid_action_fails_clearly() -> None:
    with pytest.raises(ValidationError):
        LeadRow.model_validate(
            {
                "lead_id": "lead_001",
                "company_name": "Andes ERP Partners",
                "action": "scrape_linkedin",
                "status": "new",
            }
        )


def test_invalid_status_fails_clearly() -> None:
    with pytest.raises(ValidationError):
        LeadRow.model_validate(
            {
                "lead_id": "lead_001",
                "company_name": "Andes ERP Partners",
                "action": "research_and_draft",
                "status": "done-ish",
            }
        )


def test_legacy_discard_status_normalizes_to_discarded() -> None:
    lead = LeadRow.model_validate(
        {
            "lead_id": "lead_001",
            "company_name": "Andes ERP Partners",
            "action": "research_and_draft",
            "status": "discard",
        }
    )

    assert lead.status is LeadStatus.DISCARDED


def test_needs_review_status_is_valid_for_enrichment_review_gate() -> None:
    lead = LeadRow.model_validate(
        {
            "lead_id": "lead_review",
            "company_name": "Review Co",
            "action": "research_and_draft",
            "status": "needs_review",
        }
    )

    assert lead.status is LeadStatus.NEEDS_REVIEW


def test_revision_action_requires_instruction() -> None:
    with pytest.raises(ValidationError):
        LeadRow.model_validate(
            {
                "lead_id": "lead_001",
                "company_name": "Andes ERP Partners",
                "action": "revise",
                "status": "drafted",
            }
        )


def test_demo_dataset_contains_expected_case_types() -> None:
    rows = list(csv.DictReader(Path("examples/leads_demo.csv").open(encoding="utf-8")))
    valid_rows = []
    invalid_rows = []

    for row in rows:
        try:
            valid_rows.append(LeadRow.from_mapping(row))
        except ValidationError:
            invalid_rows.append(row)

    assert len(valid_rows) == 3
    assert len(invalid_rows) == 1
    assert {row.lead_id for row in valid_rows} >= {
        "lead_good_001",
        "lead_weak_001",
        "lead_revision_001",
    }
    assert invalid_rows[0]["lead_id"] == "lead_failed_001"
