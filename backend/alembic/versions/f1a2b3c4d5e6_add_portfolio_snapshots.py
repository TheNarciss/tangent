"""add portfolio_snapshots

A daily snapshot of the investable pocket: total value and the quantities
behind it. Comparing two consecutive snapshots separates what the market
did from what the user paid in, which is what TWR, TRI and the −10 % alert
all need. Powens syncs no transaction for investment wrappers, so this is
the only place that history can come from; it starts the day it is enabled.

Revision ID: f1a2b3c4d5e6
Revises: e5f7a9c1d2b4
Create Date: 2026-09-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e5f7a9c1d2b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("total_value", sa.Float(), nullable=False),
        sa.Column("quantities", postgresql.JSONB(), nullable=False),
        sa.Column("net_flow", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "snapshot_date", name="uq_snapshot_user_date"),
    )
    op.create_index(
        "ix_portfolio_snapshots_user_date",
        "portfolio_snapshots",
        ["user_id", "snapshot_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_portfolio_snapshots_user_date", table_name="portfolio_snapshots")
    op.drop_table("portfolio_snapshots")
