"""add portfolio_reviews and llm_daily_cost tables

Revision ID: 5d8e7a2c1f3b
Revises: 6f4a2b8d1c9e
Create Date: 2026-06-02 22:30:00.000000

See ADR-015 for context. Two new tables:

- `portfolio_reviews`: 1 row per (user x calendar day). Stores the generated
  markdown, generation metadata (model, token counts, cost), cited sources,
  and the anonymized wealth snapshot sent to the LLM (for audit).
- `llm_daily_cost`: 1 row per calendar day, incremented atomically after each
  successful generation. Drives the EUR 5/day global kill-switch.

Both tables filter by `user_id` where applicable (multi-tenancy, ADR-002).
`llm_daily_cost` is intentionally global (no user_id): the kill-switch is
global, not per-user. Per-user caps are out of scope (cf ADR-015).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d8e7a2c1f3b"
down_revision: str | Sequence[str] | None = "6f4a2b8d1c9e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # -- portfolio_reviews ----------------------------------------------------
    op.create_table(
        "portfolio_reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("review_date", sa.Date(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("model_used", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("web_searches_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "wealth_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "review_date", name="uq_review_user_date"),
    )
    op.create_index(
        op.f("ix_portfolio_reviews_user_id"),
        "portfolio_reviews",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_portfolio_reviews_review_date"),
        "portfolio_reviews",
        ["review_date"],
        unique=False,
    )

    # -- llm_daily_cost -------------------------------------------------------
    op.create_table(
        "llm_daily_cost",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("cost_date", sa.Date(), nullable=False),
        sa.Column("cumulative_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reviews_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cost_date", name="uq_llm_daily_cost_date"),
    )
    op.create_index(
        op.f("ix_llm_daily_cost_cost_date"),
        "llm_daily_cost",
        ["cost_date"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_llm_daily_cost_cost_date"), table_name="llm_daily_cost")
    op.drop_table("llm_daily_cost")
    op.drop_index(op.f("ix_portfolio_reviews_review_date"), table_name="portfolio_reviews")
    op.drop_index(op.f("ix_portfolio_reviews_user_id"), table_name="portfolio_reviews")
    op.drop_table("portfolio_reviews")
