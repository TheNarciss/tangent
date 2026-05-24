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
from enum import StrEnum

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
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..auth.models import Base


class TransactionKind(StrEnum):
    """Type de transaction PEA / portefeuille."""

    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    DEPOSIT = "deposit"  # virement entrant
    WITHDRAWAL = "withdrawal"  # virement sortant
    FEE = "fee"


class Portfolio(Base):
    """1 portfolio par user. Stocke uniquement le cash dispo + métadonnées.
    Les positions sont dans une table séparée."""

    __tablename__ = "portfolios"
    __table_args__ = (UniqueConstraint("user_id", name="uq_portfolio_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    cash: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relations
    positions: Mapped[list[Position]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Position(Base):
    """N positions par portfolio. Un ticker = une ligne (PAMP = avg_cost)."""

    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "ticker", name="uq_position_portfolio_ticker"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Champs optionnels (enrichis via Powens en Phase 5)
    isin: Mapped[str | None] = mapped_column(String(12), default=None)
    label: Mapped[str | None] = mapped_column(String(128), default=None)

    portfolio: Mapped[Portfolio] = relationship(back_populates="positions")


class Transaction(Base):
    """Historique des transactions du PEA — achat, vente, dividende, frais, etc.

    Indépendant du Portfolio : si on supprime le portfolio, on garde l'historique
    (utile pour audit / re-derivation).
    """

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    kind: Mapped[TransactionKind] = mapped_column(SQLEnum(TransactionKind), nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(32), default=None, index=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


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

    # Ceilings utilisés par enveloppe — stocké en JSONB pour flexibilité
    # Ex: {"livret_a": 5000, "ldds": 0, "lep": 0, "pel": 0, "livret_a_jeune": 1000}
    ceilings_used: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class PowensCredential(Base):
    """Stocke le user_token Powens chiffré par utilisateur."""

    __tablename__ = "powens_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    encrypted_token: Mapped[str] = mapped_column(String, nullable=False)

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
