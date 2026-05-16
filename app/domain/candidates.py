from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CandidateStatus(StrEnum):
    NEW = "new"
    IMPORTED = "imported"
    DUPLICATE = "duplicate"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    VALIDATED = "validated"
    READY_FOR_ENRICHMENT = "ready_for_enrichment"
    DISQUALIFIED = "disqualified"
    PROMOTED_TO_LEAD = "promoted_to_lead"


class CandidateAction(StrEnum):
    IMPORT = "import"
    PROMOTE = "promote"
    REJECT = "reject"
    REVIEW = "review"


class SourceProvider(StrEnum):
    APOLLO = "apollo"
    SNOV = "snov"
    HUNTER = "hunter"
    FINDYMAIL = "findymail"
    GENERIC = "generic"


class SourceCandidate(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    candidate_id: str
    source_provider: SourceProvider
    source_record_id: str | None = None
    source_url: str | None = None
    company_name: str
    company_website: str | None = None
    company_domain: str | None = None
    company_linkedin_url: str | None = None
    prospect_name: str | None = None
    prospect_title: str | None = None
    prospect_linkedin_url: str | None = None
    prospect_email: str | None = None
    country: str | None = None
    region: str | None = None
    industry: str | None = None
    company_size: str | None = None
    raw_headline: str | None = None
    raw_company_description: str | None = None
    raw_data_json: dict[str, Any] | None = None
    candidate_status: CandidateStatus = CandidateStatus.NEW
    candidate_score: int | None = Field(default=None, ge=0, le=100)
    candidate_score_reason: str | None = None
    apollo_enrichment_status: str | None = None
    apollo_enrichment_reason: str | None = None
    apollo_enrichment_score: int | None = Field(default=None, ge=0, le=100)
    apollo_enrichment_confidence: int | None = Field(default=None, ge=0, le=100)
    apollo_email_enriched_at: str | None = None
    apollo_credits_used: int | None = Field(default=None, ge=0)
    manual_company_linkedin_text: str | None = None
    manual_person_linkedin_text: str | None = None
    manual_company_linkedin_copied_at: str | None = None
    manual_person_linkedin_copied_at: str | None = None
    identity_validation_status: str | None = None
    identity_validation_reason: str | None = None
    icp_status: str | None = None
    icp_score: int | None = Field(default=None, ge=0, le=100)
    icp_score_reason: str | None = None
    ready_for_enrichment: bool = False
    ready_for_draft: bool = False
    dedupe_key: str | None = None
    duplicate_of: str | None = None
    import_batch_id: str | None = None
    created_at: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    notes: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def blank_strings_become_none(cls, value: Any) -> Any:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("candidate_id", "company_name")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field is required")
        return value

    @field_validator("prospect_email")
    @classmethod
    def email_must_look_valid(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("prospect_email must look like an email address")
        return value

    @field_validator("ready_for_enrichment", "ready_for_draft", mode="before")
    @classmethod
    def blank_booleans_become_false(cls, value: Any) -> bool:
        if value is None or value == "":
            return False
        return value

    @model_validator(mode="after")
    def generate_domain_if_missing(self) -> "SourceCandidate":
        if self.company_domain is None:
            if self.company_website:
                domain = self.company_website.lower()
                domain = domain.removeprefix("https://").removeprefix("http://").removeprefix("www.")
                domain = domain.split("/")[0]
                self.company_domain = domain
            elif self.prospect_email and "@" in self.prospect_email:
                self.company_domain = self.prospect_email.split("@")[1].lower()
        return self

    @model_validator(mode="after")
    def normalize_email_if_present(self) -> "SourceCandidate":
        if self.prospect_email:
            self.prospect_email = self.prospect_email.lower().strip()
        return self

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "SourceCandidate":
        return cls.model_validate(row)


class ImportBatchStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class ImportBatch(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    import_batch_id: str
    source_provider: SourceProvider
    source_type: str = "csv"
    file_name: str | None = None
    created_by: str | None = None
    created_at: str | None = None
    total_rows: int = 0
    imported_count: int = 0
    duplicate_count: int = 0
    rejected_count: int = 0
    error_count: int = 0
    status: ImportBatchStatus = ImportBatchStatus.RUNNING
    notes: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def blank_strings_become_none(cls, value: Any) -> Any:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("import_batch_id", "source_provider")
    @classmethod
    def required_fields_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field is required")
        return value
