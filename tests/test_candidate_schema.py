import pytest
from pydantic import ValidationError

from app.domain.candidates import (
    CandidateAction,
    CandidateStatus,
    ImportBatch,
    ImportBatchStatus,
    SourceCandidate,
    SourceProvider,
)


def test_source_candidate_validates_required_fields() -> None:
    candidate = SourceCandidate.model_validate(
        {
            "candidate_id": "cand_001",
            "source_provider": "apollo",
            "company_name": "Andes ERP Partners",
            "candidate_status": "new",
        }
    )
    assert candidate.candidate_id == "cand_001"
    assert candidate.source_provider is SourceProvider.APOLLO
    assert candidate.candidate_status is CandidateStatus.NEW


def test_invalid_source_provider_fails() -> None:
    with pytest.raises(ValidationError):
        SourceCandidate.model_validate(
            {
                "candidate_id": "cand_001",
                "source_provider": "linkedin_scraper",
                "company_name": "Andes ERP Partners",
            }
        )


def test_invalid_candidate_status_fails() -> None:
    with pytest.raises(ValidationError):
        SourceCandidate.model_validate(
            {
                "candidate_id": "cand_001",
                "source_provider": "apollo",
                "company_name": "Andes ERP Partners",
                "candidate_status": "magic_status",
            }
        )


def test_candidate_email_validation() -> None:
    with pytest.raises(ValidationError):
        SourceCandidate.model_validate(
            {
                "candidate_id": "cand_001",
                "source_provider": "apollo",
                "company_name": "Andes ERP Partners",
                "prospect_email": "not-an-email",
            }
        )


def test_candidate_generates_domain_from_website() -> None:
    candidate = SourceCandidate.model_validate(
        {
            "candidate_id": "cand_002",
            "source_provider": "snov",
            "company_name": "CloudOps",
            "company_website": "https://www.cloudops.io/about",
        }
    )
    assert candidate.company_domain == "cloudops.io"


def test_candidate_generates_domain_from_email() -> None:
    candidate = SourceCandidate.model_validate(
        {
            "candidate_id": "cand_003",
            "source_provider": "hunter",
            "company_name": "DataLabs",
            "prospect_email": "juan@datalabs.com",
        }
    )
    assert candidate.company_domain == "datalabs.com"


def test_candidate_normalizes_email() -> None:
    candidate = SourceCandidate.model_validate(
        {
            "candidate_id": "cand_004",
            "source_provider": "findymail",
            "company_name": "DevTeam",
            "prospect_email": "  MARIA@DEVTEAM.COM  ",
        }
    )
    assert candidate.prospect_email == "maria@devteam.com"


def test_candidate_blank_strings_become_none() -> None:
    candidate = SourceCandidate.model_validate(
        {
            "candidate_id": "cand_005",
            "source_provider": "generic",
            "company_name": "EmptyCorp",
            "prospect_title": "   ",
        }
    )
    assert candidate.prospect_title is None


def test_import_batch_validates_required_fields() -> None:
    batch = ImportBatch.model_validate(
        {
            "import_batch_id": "batch_001",
            "source_provider": "apollo",
            "file_name": "apollo_export.csv",
            "total_rows": 100,
        }
    )
    assert batch.import_batch_id == "batch_001"
    assert batch.status is ImportBatchStatus.RUNNING
    assert batch.imported_count == 0


def test_import_batch_invalid_status_fails() -> None:
    with pytest.raises(ValidationError):
        ImportBatch.model_validate(
            {
                "import_batch_id": "batch_002",
                "source_provider": "snov",
                "status": "done",
            }
        )


def test_candidate_enums_expected_values() -> None:
    assert CandidateStatus.NEW == "new"
    assert CandidateStatus.IMPORTED == "imported"
    assert CandidateStatus.DUPLICATE == "duplicate"
    assert CandidateStatus.NEEDS_REVIEW == "needs_review"
    assert CandidateStatus.REJECTED == "rejected"
    assert CandidateStatus.PROMOTED_TO_LEAD == "promoted_to_lead"

    assert CandidateAction.IMPORT == "import"
    assert CandidateAction.PROMOTE == "promote"
    assert CandidateAction.REJECT == "reject"
    assert CandidateAction.REVIEW == "review"

    assert SourceProvider.APOLLO == "apollo"
    assert SourceProvider.SNOV == "snov"
    assert SourceProvider.HUNTER == "hunter"
    assert SourceProvider.FINDYMAIL == "findymail"
    assert SourceProvider.GENERIC == "generic"
