"""Profile v2: risk slider, household, monthly savings

Adds to profiles:
- risk_level INTEGER NULL (1..5, slider « prudent ↔ dynamique »)
- household_status VARCHAR(16) NULL ('single' | 'couple')
- children INTEGER NULL
- monthly_dca FLOAT NULL (€/mois)

target_annual_return / max_annual_volatility stay: they are now derived
from risk_level on PUT /profile and still read by the optimizer and the
LLM briefing.

Revision ID: d4e6f8a1b2c3
Revises: c8d1f5e9b6a4
Create Date: 2026-09-07
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "d4e6f8a1b2c3"
down_revision = "c8d1f5e9b6a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("risk_level", sa.Integer(), nullable=True))
    op.add_column("profiles", sa.Column("household_status", sa.String(length=16), nullable=True))
    op.add_column("profiles", sa.Column("children", sa.Integer(), nullable=True))
    op.add_column("profiles", sa.Column("monthly_dca", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "monthly_dca")
    op.drop_column("profiles", "children")
    op.drop_column("profiles", "household_status")
    op.drop_column("profiles", "risk_level")
