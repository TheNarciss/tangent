"""add goal_amount to profiles

The « combien épargner pour ton objectif » verdict (ADR-023) needs one
dated goal: the amount lives here, the date is `horizon_years`.

Revision ID: e5f7a9c1d2b4
Revises: d4e6f8a1b2c3
Create Date: 2026-09-08
"""

import sqlalchemy as sa

from alembic import op

revision = "e5f7a9c1d2b4"
down_revision = "d4e6f8a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("goal_amount", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "goal_amount")
