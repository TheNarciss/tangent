"""add locale to profiles

The language a person reads Tangent in (ADR-036): the frontend writes it
with every profile sync, so the jobs that run with no request (the morning
briefing, the archive) speak the same language as the screen. Null means
French, as before.

Revision ID: b8c3d5e7f9a2
Revises: a7b2c4d6e8f1
Create Date: 2026-09-16
"""

import sqlalchemy as sa

from alembic import op

revision = "b8c3d5e7f9a2"
down_revision = "a7b2c4d6e8f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("locale", sa.String(2), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "locale")
