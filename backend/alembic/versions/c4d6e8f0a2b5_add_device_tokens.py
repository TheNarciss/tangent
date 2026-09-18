"""add device_tokens

Which phones to tell when a briefing is ready (ADR-037). The token is
Apple's address for one app on one phone: unique, stored in the clear,
dropped as soon as Apple says it no longer leads anywhere.

Revision ID: c4d6e8f0a2b5
Revises: b8c3d5e7f9a2
Create Date: 2026-09-18
"""

import sqlalchemy as sa

from alembic import op

revision = "c4d6e8f0a2b5"
down_revision = "b8c3d5e7f9a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token", sa.String(length=200), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("locale", sa.String(length=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_device_tokens_token"),
    )
    op.create_index("ix_device_tokens_user_id", "device_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_device_tokens_user_id", table_name="device_tokens")
    op.drop_table("device_tokens")
