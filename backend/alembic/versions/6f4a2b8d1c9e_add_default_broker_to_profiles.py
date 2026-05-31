"""add default_broker to profiles

Revision ID: 6f4a2b8d1c9e
Revises: b23c3b5ca175
Create Date: 2026-05-31 14:00:00.000000

Adds `default_broker` column (nullable) on `profiles`. The user's preferred
broker is now stored per-user, autodetected from bank_accounts.institution_name
at first sync, and used by /projection for fee calculation. Backward
compatible: NULL falls back to the YAML default_broker.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "6f4a2b8d1c9e"
down_revision: str | Sequence[str] | None = "b23c3b5ca175"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column("default_broker", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("profiles", "default_broker")
