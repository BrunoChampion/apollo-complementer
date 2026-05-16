from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EnrichmentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    ENRICHED = "enriched"
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_DATA = "insufficient_data"
    FAILED = "failed"


class RecommendedAction(StrEnum):
    DRAFT = "draft"
    NEEDS_MANUAL_RESEARCH = "needs_manual_research"
    NEEDS_EMAIL_VERIFICATION = "needs_email_verification"
    DISCARD = "discard"
    WAIT = "wait"


class EvidenceSourceType(StrEnum):
    WEBSITE = "website"
    CAREERS = "careers"
    HELP_CENTER = "help_center"
    BLOG = "blog"
    APOLLO = "apollo"
    MANUAL_CONTEXT = "manual_context"
    SEARCH_RESULT = "search_result"
    UNKNOWN = "unknown"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    claim: str
    source_type: EvidenceSourceType = EvidenceSourceType.UNKNOWN
    source_url: str | None = None
    quote_or_summary: str | None = None
    confidence: int = Field(default=50, ge=0, le=100)
    used_in_message: bool = False
    created_at: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def blank_strings_become_none(cls, value: Any) -> Any:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("claim")
    @classmethod
    def claim_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("claim is required")
        return value


class EnrichmentResult(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    enrichment_id: str
    run_id: str | None = None
    lead_id: str | None = None
    company_name: str | None = None
    company_website: str | None = None
    company_domain: str | None = None
    company_linkedin_url: str | None = None
    prospect_name: str | None = None
    prospect_title: str | None = None
    prospect_linkedin_url: str | None = None
    country: str | None = None
    industry: str | None = None
    company_size: str | None = None
    enrichment_status: EnrichmentStatus = EnrichmentStatus.PENDING
    company_summary: str | None = None
    b2b_fit: bool | None = None
    operational_pain_hypothesis: str | None = None
    possible_ai_use_case: str | None = None
    personalization_angle: str | None = None
    trigger_summary: str | None = None
    risk_flags: list[str] | None = None
    review_required: bool = False
    review_category: str | None = None
    review_summary: str | None = None
    review_evidence: str | None = None
    suggested_action: str | None = None
    suggested_action_reason: str | None = None
    user_decision: str | None = None
    user_decision_notes: str | None = None
    evidence_count: int = 0
    evidence_sources: list[str] | None = None
    confidence_score: int | None = Field(default=None, ge=0, le=100)
    recommended_action: RecommendedAction = RecommendedAction.NEEDS_MANUAL_RESEARCH
    error_message: str | None = None
    created_at: str | None = None
    finished_at: str | None = None
    evidence_items: list[EvidenceItem] | None = None

    @field_validator("*", mode="before")
    @classmethod
    def blank_strings_become_none(cls, value: Any) -> Any:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("enrichment_id")
    @classmethod
    def enrichment_id_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("enrichment_id is required")
        return value

    @field_validator("review_required", mode="before")
    @classmethod
    def blank_review_required_becomes_false(cls, value: Any) -> bool:
        if value is None or value == "":
            return False
        return value

    @model_validator(mode="after")
    def compute_evidence_count(self) -> "EnrichmentResult":
        if self.evidence_items:
            self.evidence_count = len(self.evidence_items)
            self.evidence_sources = sorted(
                {item.source_type.value for item in self.evidence_items}
            )
        return self
