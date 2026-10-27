"""add finverse_connections

One bank linked through Finverse Link, per user. The refresh token is the
credential and is stored encrypted, like the Powens token (ADR-037).

Revision ID: c4d6e8f0a2b1
Revises: b8c3d5e7f9a2
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "c4d6e8f0a2b1"
down_revision = "b8c3d5e7f9a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finverse_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("login_identity_id", sa.String(length=64), nullable=False),
        sa.Column("encrypted_refresh_token", sa.String(), nullable=False),
        sa.Column("institution_name", sa.String(length=128), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id", "login_identity_id", name="uq_finverse_user_login_identity"
        ),
    )
    op.create_index("ix_finverse_connections_user_id", "finverse_connections", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_finverse_connections_user_id", table_name="finverse_connections")
    op.drop_table("finverse_connections")
