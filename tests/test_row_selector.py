from app.domain.leads import LeadAction
from app.integrations.sheets.base import SheetRow
from app.integrations.sheets.fake import FakeSheetClient
from app.services.row_selector import select_pending_rows, select_pending_rows_with_rejections


def test_selects_pending_rows_from_fake_sheet_fixture() -> None:
    client = FakeSheetClient("tests/fixtures/leads_sample.csv")

    pending = select_pending_rows(client.read_rows())

    assert [item.lead.lead_id for item in pending] == [
        "lead_good_001",
        "lead_revision_new_001",
        "lead_gmail_001",
    ]
    assert pending[0].lead.action is LeadAction.RESEARCH_AND_DRAFT


def test_returns_invalid_rows_as_rejections() -> None:
    client = FakeSheetClient("tests/fixtures/leads_sample.csv")

    _, rejected = select_pending_rows_with_rejections(client.read_rows())

    assert len(rejected) == 1
    assert rejected[0].values["lead_id"] == "lead_invalid_001"
    assert "company_name" in rejected[0].error_message


def test_revision_count_limit_prevents_unbounded_revisions() -> None:
    rows = [
        SheetRow(
            row_number=2,
            values={
                "lead_id": "lead_revision_limit",
                "company_name": "Revision Limit Co",
                "action": "revise",
                "status": "revised",
                "revision_instruction": "Hazlo mas corto.",
                "revision_count": "2",
            },
        )
    ]

    pending = select_pending_rows(rows, max_revision_count_without_override=2)

    assert pending == []


def test_existing_gmail_draft_id_prevents_duplicate_creation() -> None:
    rows = [
        SheetRow(
            row_number=2,
            values={
                "lead_id": "lead_gmail_existing",
                "company_name": "Existing Draft Co",
                "prospect_email": "ana@example.com",
                "action": "create_gmail_draft",
                "status": "approved",
                "approved": "true",
                "final_message": "Mensaje aprobado.",
                "gmail_draft_id": "draft_existing",
            },
        )
    ]

    pending = select_pending_rows(rows)

    assert pending == []
