"""extend bank_accounts hot fields + add loans table + raw_data jsonb (ADR-013)

Revision ID: 7a3f8c2d4e1b
Revises: f3213d0e26ff
Create Date: 2026-05-26 15:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "7a3f8c2d4e1b"
down_revision: str | Sequence[str] | None = "f3213d0e26ff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("bank_accounts", sa.Column("bic", sa.String(length=11), nullable=True))
    op.add_column("bank_accounts", sa.Column("number", sa.String(length=64), nullable=True))
    op.add_column("bank_accounts", sa.Column("valuation", sa.Float(), nullable=True))
    op.add_column("bank_accounts", sa.Column("diff", sa.Float(), nullable=True))
    op.add_column("bank_accounts", sa.Column("diff_percent", sa.Float(), nullable=True))
    op.add_column("bank_accounts", sa.Column("prev_diff", sa.Float(), nullable=True))
    op.add_column("bank_accounts", sa.Column("prev_diff_percent", sa.Float(), nullable=True))
    op.add_column("bank_accounts", sa.Column("coming", sa.Float(), nullable=True))
    op.add_column("bank_accounts", sa.Column("coming_balance", sa.Float(), nullable=True))
    op.add_column("bank_accounts", sa.Column("usage", sa.String(length=8), nullable=True))
    op.add_column("bank_accounts", sa.Column("ownership", sa.String(length=20), nullable=True))
    op.add_column("bank_accounts", sa.Column("company_name", sa.String(length=255), nullable=True))
    op.add_column("bank_accounts", sa.Column("bookmarked", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("bank_accounts", sa.Column("display", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("bank_accounts", sa.Column("powens_deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bank_accounts", sa.Column("powens_disabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bank_accounts", sa.Column("powens_error", sa.String(length=64), nullable=True))
    op.add_column("bank_accounts", sa.Column("powens_last_update", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bank_accounts", sa.Column("opening_date", sa.Date(), nullable=True))
    op.add_column(
        "bank_accounts",
        sa.Column(
            "raw_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.create_index(op.f("ix_bank_accounts_bookmarked"), "bank_accounts", ["bookmarked"], unique=False)

    op.create_table(
        "loans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("bank_account_id", sa.UUID(), nullable=False),
        sa.Column("total_amount", sa.Float(), nullable=True),
        sa.Column("available_amount", sa.Float(), nullable=True),
        sa.Column("used_amount", sa.Float(), nullable=True),
        sa.Column("subscription_date", sa.Date(), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("start_repayment_date", sa.Date(), nullable=True),
        sa.Column("deferred", sa.Boolean(), nullable=True),
        sa.Column("next_payment_amount", sa.Float(), nullable=True),
        sa.Column("next_payment_date", sa.Date(), nullable=True),
        sa.Column("last_payment_amount", sa.Float(), nullable=True),
        sa.Column("last_payment_date", sa.Date(), nullable=True),
        sa.Column("nb_payments_done", sa.Integer(), nullable=True),
        sa.Column("nb_payments_left", sa.Integer(), nullable=True),
        sa.Column("nb_payments_total", sa.Integer(), nullable=True),
        sa.Column("rate", sa.Float(), nullable=True),
        sa.Column("duration_months", sa.Integer(), nullable=True),
        sa.Column("insurance_label", sa.String(length=255), nullable=True),
        sa.Column("insurance_amount", sa.Float(), nullable=True),
        sa.Column("insurance_rate", sa.Float(), nullable=True),
        sa.Column("account_label", sa.String(length=255), nullable=True),
        sa.Column("loan_type", sa.String(length=32), nullable=True),
        sa.Column(
            "raw_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bank_account_id"], ["bank_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bank_account_id", name="uq_loans_bank_account_id"),
    )
    op.create_index(op.f("ix_loans_user_id"), "loans", ["user_id"], unique=False)
    op.create_index(op.f("ix_loans_maturity_date"), "loans", ["maturity_date"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_loans_maturity_date"), table_name="loans")
    op.drop_index(op.f("ix_loans_user_id"), table_name="loans")
    op.drop_table("loans")
    op.drop_index(op.f("ix_bank_accounts_bookmarked"), table_name="bank_accounts")
    op.drop_column("bank_accounts", "raw_data")
    op.drop_column("bank_accounts", "opening_date")
    op.drop_column("bank_accounts", "powens_last_update")
    op.drop_column("bank_accounts", "powens_error")
    op.drop_column("bank_accounts", "powens_disabled_at")
    op.drop_column("bank_accounts", "powens_deleted_at")
    op.drop_column("bank_accounts", "display")
    op.drop_column("bank_accounts", "bookmarked")
    op.drop_column("bank_accounts", "company_name")
    op.drop_column("bank_accounts", "ownership")
    op.drop_column("bank_accounts", "usage")
    op.drop_column("bank_accounts", "coming_balance")
    op.drop_column("bank_accounts", "coming")
    op.drop_column("bank_accounts", "prev_diff_percent")
    op.drop_column("bank_accounts", "prev_diff")
    op.drop_column("bank_accounts", "diff_percent")
    op.drop_column("bank_accounts", "diff")
    op.drop_column("bank_accounts", "valuation")
    op.drop_column("bank_accounts", "number")
    op.drop_column("bank_accounts", "bic")
