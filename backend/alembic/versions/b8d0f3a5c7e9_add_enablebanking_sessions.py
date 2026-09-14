"""add enablebanking_sessions

One PSD2 consent at one bank through Enable Banking, per user. The session
id is the credential and is stored encrypted, like the Powens token.

Revision ID: b8d0f3a5c7e9
Revises: a7c9e2b4d6f8
Create Date: 2026-09-14
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "b8d0f3a5c7e9"
down_revision = "a7c9e2b4d6f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enablebanking_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("encrypted_session_id", sa.String(), nullable=False),
        sa.Column("bank_name", sa.String(length=64), nullable=False),
        sa.Column("bank_country", sa.String(length=2), nullable=False),
        sa.Column("psu_type", sa.String(length=16), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_enablebanking_sessions_user_id", "enablebanking_sessions", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_enablebanking_sessions_user_id", table_name="enablebanking_sessions")
    op.drop_table("enablebanking_sessions")
