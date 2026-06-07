"""Add review_batches table + auto_review_enabled flag

Adds:
- profiles.auto_review_enabled BOOLEAN NOT NULL DEFAULT FALSE
- review_batches table (Anthropic batch tracking)
- portfolio_reviews.batch_id UUID NULL FK -> review_batches(id) ON DELETE SET NULL
- portfolio_reviews.generation_mode VARCHAR(16) NOT NULL DEFAULT 'manual'

Hand-written (not autogenerate) because autogenerate omits server_default on
NOT NULL columns, which would break backfill for existing rows.

Revision ID: b7e2c9d3a5f1
Revises: 5d8e7a2c1f3b
Create Date: 2026-06-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b7e2c9d3a5f1"
down_revision = "5d8e7a2c1f3b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. profiles.auto_review_enabled (NOT NULL + default for existing rows)
    op.add_column(
        "profiles",
        sa.Column(
            "auto_review_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # 2. review_batches table
    op.create_table(
        "review_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("anthropic_batch_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("n_requests", sa.Integer(), nullable=False),
        sa.Column("n_succeeded", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("n_errored", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("n_expired", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("actual_cost_usd", sa.Float(), nullable=True),
    )
    op.create_index(
        "ix_review_batches_submitted_at",
        "review_batches",
        ["submitted_at"],
    )

    # 3. portfolio_reviews.batch_id + generation_mode
    op.add_column(
        "portfolio_reviews",
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "portfolio_reviews",
        sa.Column(
            "generation_mode",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
    )
    op.create_foreign_key(
        "fk_portfolio_reviews_batch_id",
        "portfolio_reviews",
        "review_batches",
        ["batch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_portfolio_reviews_batch_id",
        "portfolio_reviews",
        ["batch_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_reviews_batch_id", table_name="portfolio_reviews")
    op.drop_constraint(
        "fk_portfolio_reviews_batch_id",
        "portfolio_reviews",
        type_="foreignkey",
    )
    op.drop_column("portfolio_reviews", "generation_mode")
    op.drop_column("portfolio_reviews", "batch_id")

    op.drop_index("ix_review_batches_submitted_at", table_name="review_batches")
    op.drop_table("review_batches")

    op.drop_column("profiles", "auto_review_enabled")
