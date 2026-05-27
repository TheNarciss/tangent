"""Modèle User en base — SQLAlchemy 2.0 async.

FastAPI-Users impose son propre type de base UserTable (UUID id par défaut).
On utilise leur SQLAlchemyBaseUserTableUUID qui inclut déjà :
- id (UUID, PK)
- email (unique, indexed)
- hashed_password — overridé nullable depuis ADR-014 pour les users OAuth-only
- is_active (bool, default True)
- is_superuser (bool, default False)
- is_verified (bool, default False)

On ajoute :
- display_name (optionnel, affiché dans l'UI)
- created_at, updated_at (audit)
- oauth_accounts (relationship vers OAuthAccount, cf ADR-014)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .oauth_models import OAuthAccount


class Base(DeclarativeBase):
    """Base SQLAlchemy commune à toutes les tables du projet."""


class User(SQLAlchemyBaseUserTableUUID, Base):
    """Table users. SQLAlchemyBaseUserTableUUID fournit id/email/hashed_password/flags.

    hashed_password override nullable : les users Google-only n'en ont pas (ADR-014).
    Les 10+ users existants conservent leurs hashes — la nullability ouvre la
    porte aux nouveaux users sans rien casser.
    """

    __tablename__ = "users"

    # Override : nullable pour les users OAuth-only (cf ADR-014 §3)
    # Liskov violation acceptée : users OAuth-only sans password (ADR-014).
    # fastapi-users gère les deux cas au runtime (verify(None,hash)→False).
    hashed_password: Mapped[str | None] = mapped_column(  # type: ignore[assignment]
        String(1024), nullable=True
    )

    display_name: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # OAuth accounts liés (one-to-many, cf ADR-014)
    # lazy="joined" : recommandé par fastapi-users, charge en JOIN au select du User
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount",
        lazy="joined",
        cascade="all, delete-orphan",
    )
