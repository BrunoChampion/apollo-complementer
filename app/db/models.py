from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_uuid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    sheet_id: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[dict | None] = mapped_column(JSON)

    lead_runs: Mapped[list["LeadRun"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class LeadRun(Base):
    __tablename__ = "lead_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), nullable=False)
    lead_id: Mapped[str] = mapped_column(Text, nullable=False)
    row_number: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    input_snapshot: Mapped[dict | None] = mapped_column(JSON)
    output_snapshot: Mapped[dict | None] = mapped_column(JSON)

    run: Mapped[Run] = relationship(back_populates="lead_runs")
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(
        back_populates="lead_run",
        cascade="all, delete-orphan",
    )


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    lead_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("lead_runs.id"), nullable=False)
    lead_id: Mapped[str] = mapped_column(Text, nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(Text, nullable=False)
    used_in_message: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    lead_run: Mapped[LeadRun] = relationship(back_populates="evidence_items")


class EnrichmentRun(Base):
    __tablename__ = "enrichment_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str | None] = mapped_column(Text)
    lead_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    company_summary: Mapped[str | None] = mapped_column(Text)
    b2b_fit: Mapped[bool | None] = mapped_column(default=None)
    operational_pain_hypothesis: Mapped[str | None] = mapped_column(Text)
    possible_ai_use_case: Mapped[str | None] = mapped_column(Text)
    personalization_angle: Mapped[str | None] = mapped_column(Text)
    trigger_summary: Mapped[str | None] = mapped_column(Text)
    risk_flags: Mapped[list[str] | None] = mapped_column(JSON)
    confidence_score: Mapped[int | None] = mapped_column(Integer)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    evidence_items: Mapped[list["EnrichmentEvidenceItem"]] = relationship(
        back_populates="enrichment_run",
        cascade="all, delete-orphan",
    )


class SourcingJob(Base):
    __tablename__ = "sourcing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text, nullable=False, default="apollo")
    query_params: Mapped[dict | None] = mapped_column(JSON)
    max_candidates: Mapped[int] = mapped_column(Integer, default=50)
    enrich_emails: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    job_runs: Mapped[list["SourcingJobRun"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class SourcingJobRun(Base):
    __tablename__ = "sourcing_job_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("sourcing_jobs.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    candidates_found: Mapped[int] = mapped_column(Integer, default=0)
    candidates_imported: Mapped[int] = mapped_column(Integer, default=0)
    candidates_duplicated: Mapped[int] = mapped_column(Integer, default=0)
    candidates_rejected: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[dict | None] = mapped_column(JSON)

    job: Mapped[SourcingJob] = relationship(back_populates="job_runs")


class ProviderUsage(Base):
    __tablename__ = "provider_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    provider: Mapped[str] = mapped_column(Text, nullable=False, default="apollo")
    usage_type: Mapped[str] = mapped_column(Text, nullable=False, default="search")
    credits_used: Mapped[int] = mapped_column(Integer, default=1)
    meta: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EnrichmentEvidenceItem(Base):
    __tablename__ = "enrichment_evidence_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    enrichment_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enrichment_runs.id"), nullable=False
    )
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    quote_or_summary: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    used_in_message: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    enrichment_run: Mapped[EnrichmentRun] = relationship(back_populates="evidence_items")
