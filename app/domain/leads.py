from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LeadAction(StrEnum):
    RESEARCH = "research"
    DRAFT = "draft"
    RESEARCH_AND_DRAFT = "research_and_draft"
    REVISE = "revise"
    CREATE_GMAIL_DRAFT = "create_gmail_draft"
    EXPORT = "export"
    SKIP = "skip"
    IMPORT_CANDIDATES = "import_candidates"
    ENRICH = "enrich"
    ENRICH_AND_DRAFT = "enrich_and_draft"
    SOURCE_APOLLO = "source_apollo"
    VERIFY_EMAIL = "verify_email"


class LeadStatus(StrEnum):
    NEW = "new"
    QUEUED = "queued"
    PROCESSING = "processing"
    RESEARCHED = "researched"
    DRAFTED = "drafted"
    NEEDS_REVISION = "needs_revision"
    REVISED = "revised"
    APPROVED = "approved"
    GMAIL_DRAFT_CREATED = "gmail_draft_created"
    EXPORTED = "exported"
    SENT = "sent"
    ERROR = "error"
    SKIPPED = "skipped"
    IMPORTED = "imported"
    DUPLICATE = "duplicate"
    ENRICHMENT_PENDING = "enrichment_pending"
    ENRICHING = "enriching"
    ENRICHED = "enriched"
    INSUFFICIENT_DATA = "insufficient_data"
    NEEDS_MANUAL_RESEARCH = "needs_manual_research"
    NEEDS_REVIEW = "needs_review"
    NEEDS_EMAIL_VERIFICATION = "needs_email_verification"
    DISCARDED = "discarded"
    CANDIDATE_PROMOTED = "candidate_promoted"
    READY_FOR_ENRICHMENT = "ready_for_enrichment"
    READY_FOR_DRAFT = "ready_for_draft"


class LeadRow(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    lead_id: str
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
    technologies: str | None = None
    annual_revenue: str | None = None
    total_funding: str | None = None
    latest_funding: str | None = None
    latest_funding_amount: str | None = None
    apollo_contact_id: str | None = None
    apollo_account_id: str | None = None
    source: str | None = None

    manual_context: str | None = None
    manual_company_context: str | None = None
    manual_person_context: str | None = None
    manual_linkedin_notes: str | None = None
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
    source_url: str | None = None

    action: LeadAction = LeadAction.RESEARCH_AND_DRAFT
    status: LeadStatus = LeadStatus.NEW
    approved: bool = False

    fit_score: int | None = Field(default=None, ge=0, le=100)
    fit_score_reason: str | None = None
    quality_score: int | None = Field(default=None, ge=0, le=100)
    quality_issues: str | None = None
    evidence_quality: str | None = None
    enrichment_result: str | dict[str, Any] | None = None
    review_required: bool = False
    review_category: str | None = None
    review_summary: str | None = None
    review_evidence: str | None = None
    suggested_action: str | None = None
    suggested_action_reason: str | None = None
    user_decision: str | None = None
    user_decision_notes: str | None = None
    manual_context_summary: str | None = None
    message_angle: str | None = None
    email_subject: str | None = None
    email_draft: str | None = None
    revision_instruction: str | None = None
    revision_instruction_hash: str | None = None
    last_processed_revision_hash: str | None = None
    revised_draft: str | None = None
    revision_count: int = Field(default=0, ge=0)
    final_subject: str | None = None
    final_message: str | None = None
    gmail_draft_id: str | None = None
    gmail_draft_url: str | None = None
    export_ready: bool = False
    agent_note: str | None = None
    error_message: str | None = None
    run_id: str | None = None
    locked_at: str | None = None
    processed_at: str | None = None
    last_updated_by_agent_at: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def blank_strings_become_none(cls, value: Any) -> Any:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("lead_id", "company_name")
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

    @field_validator("status", mode="before")
    @classmethod
    def normalize_legacy_statuses(cls, value: Any) -> Any:
        if value == "discard":
            return LeadStatus.DISCARDED
        return value

    @field_validator(
        "approved",
        "export_ready",
        "ready_for_enrichment",
        "ready_for_draft",
        "review_required",
        mode="before",
    )
    @classmethod
    def blank_booleans_become_false(cls, value: Any) -> bool:
        if value is None or value == "":
            return False
        return value

    @field_validator("revision_count", mode="before")
    @classmethod
    def blank_revision_count_becomes_zero(cls, value: Any) -> int:
        if value is None or value == "":
            return 0
        return value

    @model_validator(mode="after")
    def revision_action_requires_instruction(self) -> "LeadRow":
        if self.action == LeadAction.REVISE and not self.revision_instruction:
            raise ValueError("revision_instruction is required when action is revise")
        return self

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "LeadRow":
        return cls.model_validate(row)
