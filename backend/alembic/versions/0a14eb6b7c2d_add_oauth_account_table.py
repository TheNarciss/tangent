"""add oauth_account table + users.hashed_password nullable

Revision ID: 0a14eb6b7c2d
Revises: 7a3f8c2d4e1b
Create Date: 2026-05-27 17:00:00.000000

Cf ADR-014 (Google OAuth multi-provider).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from fastapi_users_db_sqlalchemy.generics import GUID


# revision identifiers, used by Alembic.
revision: str = "0a14eb6b7c2d"
down_revision: str | Sequence[str] | None = "7a3f8c2d4e1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1) users.hashed_password → nullable (pour les users OAuth-only)
    #    Les 10+ users existants conservent leur hash, aucun impact.
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=1024),
        nullable=True,
    )

    # 2) Nouvelle table oauth_account (one-to-many users → oauth_account)
    op.create_table(
        "oauth_account",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("oauth_name", sa.String(length=100), nullable=False),
        sa.Column("access_token", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=True),
        sa.Column("refresh_token", sa.LargeBinary(), nullable=True),
        sa.Column("account_id", sa.String(length=320), nullable=False),
        sa.Column("account_email", sa.String(length=320), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_oauth_account_user_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "oauth_name",
            "account_id",
            name="uq_oauth_account_provider_id",
        ),
    )
    op.create_index(
        "ix_oauth_account_user_id",
        "oauth_account",
        ["user_id"],
    )
    op.create_index(
        "ix_oauth_account_oauth_name",
        "oauth_account",
        ["oauth_name"],
    )
    op.create_index(
        "ix_oauth_account_account_email",
        "oauth_account",
        ["account_email"],
    )


def downgrade() -> None:
    """Downgrade schema.

    WARN : revert nullable=False sur hashed_password peut échouer si des
    users OAuth-only existent (hash NULL). Procédure recommandée si rollback :
    supprimer ces users d'abord (ou leur définir un hash via reset).
    """
    op.drop_index("ix_oauth_account_account_email", table_name="oauth_account")
    op.drop_index("ix_oauth_account_oauth_name", table_name="oauth_account")
    op.drop_index("ix_oauth_account_user_id", table_name="oauth_account")
    op.drop_table("oauth_account")
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=1024),
        nullable=False,
    )
