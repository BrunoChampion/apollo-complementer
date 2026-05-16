"""add enrichment tables

Revision ID: 20260505_add_enrichment_tables
Revises:
Create Date: 2026-05-05 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260505_add_enrichment_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enrichment_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.Text(), nullable=True),
        sa.Column("lead_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, default="pending"),
        sa.Column("company_summary", sa.Text(), nullable=True),
        sa.Column("b2b_fit", sa.Boolean(), nullable=True),
        sa.Column("operational_pain_hypothesis", sa.Text(), nullable=True),
        sa.Column("possible_ai_use_case", sa.Text(), nullable=True),
        sa.Column("personalization_angle", sa.Text(), nullable=True),
        sa.Column("trigger_summary", sa.Text(), nullable=True),
        sa.Column("risk_flags", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "enrichment_evidence_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "enrichment_run_id",
            sa.String(36),
            sa.ForeignKey("enrichment_runs.id"),
            nullable=False,
        ),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("quote_or_summary", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False, default=50),
        sa.Column("used_in_message", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("enrichment_evidence_items")
    op.drop_table("enrichment_runs")
