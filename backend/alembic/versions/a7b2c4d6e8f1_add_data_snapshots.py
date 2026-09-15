"""add data_snapshots

The archive (ADR-034): twice a day, morning and evening, everything the app
knows is written down as it was — what is personal to a user (accounts,
positions, profile, what the method concluded) sealed with a key the
database does not hold, and what came from the public sources (prices,
rates, the list, the leads) in the clear. One row per user and per slot,
one row per slot for the market; a rerun of the same slot replaces its row.

Revision ID: a7b2c4d6e8f1
Revises: c9e1a4b6d8f0
Create Date: 2026-09-15
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "a7b2c4d6e8f1"
down_revision = "c9e1a4b6d8f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),  # user | market
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("slot", sa.String(16), nullable=False),  # morning | evening
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),  # market: in the clear
        sa.Column("sealed", sa.Text(), nullable=True),  # user: Fernet token of the JSON
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_data_snapshots_user_slot",
        "data_snapshots",
        ["user_id", "snapshot_date", "slot"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_data_snapshots_market_slot",
        "data_snapshots",
        ["scope", "snapshot_date", "slot"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_data_snapshots_market_slot", table_name="data_snapshots")
    op.drop_index("uq_data_snapshots_user_slot", table_name="data_snapshots")
    op.drop_table("data_snapshots")
