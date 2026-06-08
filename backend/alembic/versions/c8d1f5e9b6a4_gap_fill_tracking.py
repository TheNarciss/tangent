"""Add gap-fill tracking columns (ADR-021).

Hand-written (not autogenerate) per project convention.

Adds tracking columns for the Universal Gap-Filler architecture:

- account_holdings:
  - ter: Float, nullable (resolved TER ratio, 0.0025 = 0.25%)
  - ter_source: VARCHAR(16), nullable ('api' | 'llm' | 'user' | NULL)
  - ter_resolved_at: TIMESTAMPTZ, nullable
  - isin_source: VARCHAR(16), nullable
  - isin_resolved_at: TIMESTAMPTZ, nullable

- bank_transactions (category column already exists, nullable):
  - category_source: VARCHAR(16), nullable
  - category_resolved_at: TIMESTAMPTZ, nullable

Conventions for *_source values:
  - 'api'  : value came from upstream provider (Powens, yfinance auto-detect)
  - 'llm'  : value resolved by Claude gap-fill batch (estimation, to verify)
  - 'user' : value set manually by the user (final truth)
  - NULL   : never resolved, value is NULL (legacy or genuinely unknown)

All columns nullable, no default. Existing rows have source=NULL meaning
"legacy / never gap-filled". Backfill is opt-in via the LLM gap-fill batch.

Revision ID: c8d1f5e9b6a4
Revises: b7e2c9d3a5f1
Create Date: 2026-06-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c8d1f5e9b6a4"
down_revision = "b7e2c9d3a5f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # account_holdings: TER + sources
    op.add_column(
        "account_holdings",
        sa.Column("ter", sa.Float(), nullable=True),
    )
    op.add_column(
        "account_holdings",
        sa.Column("ter_source", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "account_holdings",
        sa.Column("ter_resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "account_holdings",
        sa.Column("isin_source", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "account_holdings",
        sa.Column("isin_resolved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # bank_transactions: category tracking (category column itself already exists)
    op.add_column(
        "bank_transactions",
        sa.Column("category_source", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("category_resolved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bank_transactions", "category_resolved_at")
    op.drop_column("bank_transactions", "category_source")
    op.drop_column("account_holdings", "isin_resolved_at")
    op.drop_column("account_holdings", "isin_source")
    op.drop_column("account_holdings", "ter_resolved_at")
    op.drop_column("account_holdings", "ter_source")
    op.drop_column("account_holdings", "ter")
