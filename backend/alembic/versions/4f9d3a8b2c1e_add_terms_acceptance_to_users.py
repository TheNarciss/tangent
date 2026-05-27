"""add terms_version_accepted and terms_accepted_at to users

Revision ID: 4f9d3a8b2c1e
Revises: 0a14eb6b7c2d
Create Date: 2026-05-27 22:00:00.000000

Cf TermsGate / click-through agreement. Pas de backfill volontaire : les
users existants verront le gate à leur prochaine connexion.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f9d3a8b2c1e"
down_revision: str | Sequence[str] | None = "0a14eb6b7c2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("terms_version_accepted", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "terms_version_accepted")
