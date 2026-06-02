"""merge wealth cleanup and concurrent migration

Revision ID: b23c3b5ca175
Revises: 4f9d3a8b2c1e, a8b5d3f7e294
Create Date: 2026-05-31 15:48:17.463309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b23c3b5ca175'
down_revision: Union[str, Sequence[str], None] = ('4f9d3a8b2c1e', 'a8b5d3f7e294')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
