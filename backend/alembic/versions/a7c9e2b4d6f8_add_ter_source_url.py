"""add ter_source_url to account_holdings

The gap-filler already asks the LLM to cite the KID or factsheet it read the
TER from, and the citation was thrown away. A fee figure that drives a verdict
in euros per year has to be checkable a year later.

Revision ID: a7c9e2b4d6f8
Revises: f1a2b3c4d5e6
Create Date: 2026-09-09
"""

import sqlalchemy as sa

from alembic import op

revision = "a7c9e2b4d6f8"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "account_holdings", sa.Column("ter_source_url", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("account_holdings", "ter_source_url")
