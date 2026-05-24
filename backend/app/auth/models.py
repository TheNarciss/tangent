"""Modèle User en base — SQLAlchemy 2.0 async.

FastAPI-Users impose son propre type de base UserTable (UUID id par défaut).
On utilise leur SQLAlchemyBaseUserTableUUID qui inclut déjà :
- id (UUID, PK)
- email (unique, indexed)
- hashed_password
- is_active (bool, default True)
- is_superuser (bool, default False)
- is_verified (bool, default False)

On ajoute juste :
- created_at, updated_at (audit)
- display_name (optionnel, affiché dans l'UI)
"""

from datetime import UTC, datetime

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base SQLAlchemy commune à toutes les tables du projet."""


class User(SQLAlchemyBaseUserTableUUID, Base):
    """Table users. SQLAlchemyBaseUserTableUUID fournit id/email/hashed_password/flags."""

    __tablename__ = "users"

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
