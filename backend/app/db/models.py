"""Tables business — chaque ressource est ownée par un user.

Pattern : toutes les tables ici ont un `user_id` FK vers users.id. Les
endpoints filtrent par `user_id = current_user.id` → isolation multi-tenant
garantie au niveau DB.

Tables :
- portfolios       : 1 portfolio par user (1-to-1)
- positions        : N positions par portfolio (DCAM, PUST, etc.)
- transactions     : N transactions historiques par user (achat, vente)
- watchlist_items  : N tickers suivis par user (qty=0)
- profiles         : 1 profil financier par user (date naissance, RFR, ceilings...)
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..auth.models import Base


class WatchlistItem(Base):
    """Tickers suivis sans transaction réelle (qty=0)."""

    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "ticker", name="uq_watchlist_user_ticker"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class Profile(Base):
    """Profil financier — identité fiscale + ceilings d'enveloppes + stratégie.

    1 profil par user (1-to-1). Nullable pour permettre la création progressive
    (un user qui vient de s'inscrire peut commencer sans avoir tout rempli).
    """

    __tablename__ = "profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_profile_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Identité fiscale
    birth_date: Mapped[date | None] = mapped_column(Date, default=None)
    fiscal_shares: Mapped[float | None] = mapped_column(Float, default=None)
    rfr_n_minus_2: Mapped[float | None] = mapped_column(Float, default=None)

    # Stratégie
    target_annual_return: Mapped[float | None] = mapped_column(Float, default=None)  # en %
    max_annual_volatility: Mapped[float | None] = mapped_column(Float, default=None)  # en %
    horizon_years: Mapped[int | None] = mapped_column(Integer, default=None)
    default_broker: Mapped[str | None] = mapped_column(String(50), default=None)

    # Ceilings utilisés par enveloppe — stocké en JSONB pour flexibilité
    # Ex: {"livret_a": 5000, "ldds": 0, "lep": 0, "pel": 0, "livret_a_jeune": 1000}
    ceilings_used: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class PowensCredential(Base):
    """Stocke le user_token Powens chiffré par utilisateur + sync state (per-user).

    Multi-tenant safe: chaque user_id Tangent a sa propre ligne. Toutes les
    metadata de sync (last_sync, positions_count, etc.) sont per-user et lues
    via /sync/status filtré par user_id.
    """

    __tablename__ = "powens_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    encrypted_token: Mapped[str] = mapped_column(String, nullable=False)

    # Per-user sync state (replaces the deprecated module-level powens.state)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_webhook_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_error: Mapped[str | None] = mapped_column(Text, default=None)
    last_positions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_cash_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class PasswordResetToken(Base):
    """One-time password reset code, hashed at rest.

    The plaintext 6-digit code is sent by email; we store only its argon2 hash.
    Codes expire in 15 min and are single-use. Brute force is bounded by
    `attempts <= RESET_MAX_ATTEMPTS` and per-IP rate limiting at the router level.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


# ════════════════════════════════════════════════════════════════════════════
# Phase A — Multi-account aggregation (ADR-008)
#
# These tables coexist with the legacy Portfolio/Position/Transaction (PEA-only)
# until Phase A3 fully migrates the routes to use them. Until then, both stay.
# ════════════════════════════════════════════════════════════════════════════


class BankAccount(Base):
    """Compte bancaire individuel agrégé via un provider (Powens, Bridge...).

    1:N avec users. Source de vérité pour la liste de comptes (Phase A).

    Storage strategy: hot fields + raw_data JSONB (ADR-013).
    """

    __tablename__ = "bank_accounts"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "provider",
            "provider_account_id",
            name="uq_bank_accounts_user_provider_acc",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_account_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # ── Core identification ────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    institution_name: Mapped[str | None] = mapped_column(String(255), default=None)

    # ── Identifiers ────────────────────────────────────────────────────────
    iban: Mapped[str | None] = mapped_column(String(64), default=None)
    bic: Mapped[str | None] = mapped_column(String(11), default=None)
    number: Mapped[str | None] = mapped_column(String(64), default=None)

    # ── Balance & valuation (cf ADR-013) ───────────────────────────────────
    # `balance`     = raw balance from the bank (cash accounts, loans)
    # `valuation`   = Powens-computed sum of holdings (invest accounts only).
    #                 For invest, prefer this over `balance` (fresher).
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    valuation: Mapped[float | None] = mapped_column(Float, default=None)
    coming: Mapped[float | None] = mapped_column(Float, default=None)
    coming_balance: Mapped[float | None] = mapped_column(Float, default=None)

    # Gain/loss (computed by Powens for invest accounts)
    diff: Mapped[float | None] = mapped_column(Float, default=None)
    diff_percent: Mapped[float | None] = mapped_column(Float, default=None)
    prev_diff: Mapped[float | None] = mapped_column(Float, default=None)
    prev_diff_percent: Mapped[float | None] = mapped_column(Float, default=None)

    # ── Account context ────────────────────────────────────────────────────
    usage: Mapped[str | None] = mapped_column(String(8), default=None)  # PRIV | ORGA
    ownership: Mapped[str | None] = mapped_column(
        String(20), default=None
    )  # owner | co-owner | attorney
    company_name: Mapped[str | None] = mapped_column(String(255), default=None)  # PEE/PERCO
    opening_date: Mapped[date | None] = mapped_column(Date, default=None)

    # ── State (user-controlled or bank-side) ───────────────────────────────
    bookmarked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    display: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    powens_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    powens_disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    powens_error: Mapped[str | None] = mapped_column(String(64), default=None)
    powens_last_update: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    # ── Sync tracking ──────────────────────────────────────────────────────
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # ── Full raw Powens payload (ADR-013) ──────────────────────────────────
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # ── Relationships ──────────────────────────────────────────────────────
    holdings: Mapped[list[AccountHolding]] = relationship(
        back_populates="bank_account",
        cascade="all, delete-orphan",
    )
    bank_transactions: Mapped[list[BankTransaction]] = relationship(
        back_populates="bank_account",
        cascade="all, delete-orphan",
    )
    loan: Mapped[Loan | None] = relationship(
        back_populates="bank_account",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )


class AccountHolding(Base):
    """Position dans un compte titres (PEA / CTO / life insurance).

    1:N avec bank_accounts. Distinct de Position (legacy PEA-only).
    Replace-all pattern : à chaque sync, on wipe + re-insert pour idempotence.
    """

    __tablename__ = "account_holdings"
    __table_args__ = (
        UniqueConstraint(
            "bank_account_id",
            "provider_investment_id",
            name="uq_holdings_account_provider_inv",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider_investment_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    isin: Mapped[str | None] = mapped_column(String(12), default=None)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    bank_account: Mapped[BankAccount] = relationship(back_populates="holdings")


class BankTransaction(Base):
    """Transaction bancaire (checking / savings / card).

    1:N avec bank_accounts. Append-only pattern : on n'efface jamais les anciennes.
    """

    __tablename__ = "bank_transactions"
    __table_args__ = (
        UniqueConstraint(
            "bank_account_id",
            "provider_transaction_id",
            name="uq_bank_tx_account_provider_tx",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider_transaction_id: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    category: Mapped[str | None] = mapped_column(String(64), default=None, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    bank_account: Mapped[BankAccount] = relationship(back_populates="bank_transactions")


# Append this class at the end of backend/app/db/models.py
# (right after BankTransaction class).


class Loan(Base):
    """Détails d'un prêt — one-to-one avec un BankAccount de type loan-like.

    Présent uniquement si le BankAccount a type ∈ {loan, mortgage,
    consumercredit, revolvingcredit}.

    Storage: hot fields + raw_data JSONB (ADR-013). raw_data contient le
    Loan-object complet renvoyé par Powens, incluant les champs non-promus
    en colonne.
    """

    __tablename__ = "loans"
    __table_args__ = (UniqueConstraint("bank_account_id", name="uq_loans_bank_account_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Capital amounts ────────────────────────────────────────────────────
    total_amount: Mapped[float | None] = mapped_column(Float, default=None)
    available_amount: Mapped[float | None] = mapped_column(Float, default=None)
    used_amount: Mapped[float | None] = mapped_column(Float, default=None)

    # ── Key dates ──────────────────────────────────────────────────────────
    subscription_date: Mapped[date | None] = mapped_column(Date, default=None)
    maturity_date: Mapped[date | None] = mapped_column(Date, default=None, index=True)
    start_repayment_date: Mapped[date | None] = mapped_column(Date, default=None)
    deferred: Mapped[bool | None] = mapped_column(Boolean, default=None)

    # ── Payments ───────────────────────────────────────────────────────────
    next_payment_amount: Mapped[float | None] = mapped_column(Float, default=None)
    next_payment_date: Mapped[date | None] = mapped_column(Date, default=None)
    last_payment_amount: Mapped[float | None] = mapped_column(Float, default=None)
    last_payment_date: Mapped[date | None] = mapped_column(Date, default=None)
    nb_payments_done: Mapped[int | None] = mapped_column(Integer, default=None)
    nb_payments_left: Mapped[int | None] = mapped_column(Integer, default=None)
    nb_payments_total: Mapped[int | None] = mapped_column(Integer, default=None)

    # ── Rate & duration ────────────────────────────────────────────────────
    rate: Mapped[float | None] = mapped_column(Float, default=None)  # absolute % (2.0 = 2%)
    duration_months: Mapped[int | None] = mapped_column(Integer, default=None)

    # ── Insurance ──────────────────────────────────────────────────────────
    insurance_label: Mapped[str | None] = mapped_column(String(255), default=None)
    insurance_amount: Mapped[float | None] = mapped_column(Float, default=None)
    insurance_rate: Mapped[float | None] = mapped_column(Float, default=None)

    # ── Misc ───────────────────────────────────────────────────────────────
    account_label: Mapped[str | None] = mapped_column(String(255), default=None)
    loan_type: Mapped[str | None] = mapped_column(String(32), default=None)

    # ── Full raw Powens payload (ADR-013) ──────────────────────────────────
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # ── Timestamps ─────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # ── Relationships ──────────────────────────────────────────────────────
    bank_account: Mapped[BankAccount] = relationship(back_populates="loan")


# ─────────────────────────────────────────────────────────────────────────────
# Append this block to backend/app/db/models.py (after the Loan class).
# See ADR-015 for context.
# ─────────────────────────────────────────────────────────────────────────────


class PortfolioReview(Base):
    """Generated LLM review of a user's complete patrimony.

    Generated on demand (manual button), max 1 per (user × calendar day in
    Europe/Paris). The UNIQUE constraint on `(user_id, review_date)` enforces
    the cap at the DB level — concurrent generation attempts race on the
    INSERT and one of them gets `IntegrityError`, surfaced to the user as
    HTTP 409 by the route layer.

    See ADR-015 §Frequency cap.
    """

    __tablename__ = "portfolio_reviews"
    __table_args__ = (UniqueConstraint("user_id", "review_date", name="uq_review_user_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    review_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # ── Content (markdown) ────────────────────────────────────────────────
    content: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    # ── Generation metadata ───────────────────────────────────────────────
    model_used: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    web_searches_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── Citations (URLs returned by web_search tool) ──────────────────────
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # ── Anonymized wealth snapshot at generation time (for audit) ─────────
    # Note: anonymization happens at prompt_builder.py — no PII (names,
    # account IDs) ever reaches this column.
    wealth_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class LLMDailyCost(Base):
    """Daily aggregate of LLM spend — drives the global kill-switch.

    1 row per calendar day (Europe/Paris). Incremented atomically via PG
    UPSERT (`INSERT ... ON CONFLICT (cost_date) DO UPDATE SET
    cumulative_cost_usd = cumulative_cost_usd + EXCLUDED.cumulative_cost_usd`)
    after each successful generation.

    No `user_id`: the kill-switch is global (ADR-015 §Cost cap). Per-user
    caps are out of scope today.
    """

    __tablename__ = "llm_daily_cost"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cost_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    cumulative_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reviews_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
