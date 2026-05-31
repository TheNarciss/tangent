"""drop legacy portfolios, positions, transactions tables

Revision ID: a8b5d3f7e294
Revises: 7a3f8c2d4e1b
Create Date: 2026-05-31 12:00:00.000000

Phase 2 PR 6 cleanup: removes the Portfolio + Position tables (legacy
single-PEA flow) and the unused Transaction table. Positions are now sourced
exclusively from Powens (bank_accounts + account_holdings) and projected
into the Wealth domain.

Data loss: any rows in these tables are destroyed. Powens will recreate
the positions at the next sync.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a8b5d3f7e294"
down_revision: str | Sequence[str] | None = "7a3f8c2d4e1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop positions THEN portfolios (FK order). Drop transactions (no FK)."""
    op.drop_table("positions")
    op.drop_table("portfolios")
    op.drop_table("transactions")


def downgrade() -> None:
    """Recreate the legacy schema. Data is gone — schema only."""
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("cash", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("avg_cost", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
