"""Modèle OAuthAccount — comptes OAuth tiers liés à un User (cf ADR-014).

Une ligne par (user, provider). Plusieurs providers possibles par user.
Le mixin fastapi-users fournit la majorité des colonnes ; on override :
- user_id pour pointer sur `users.id` (le mixin default est `user.id` singulier)
- access_token et refresh_token pour chiffrement Fernet (ADR-014 §5)
"""

from __future__ import annotations

import uuid

from fastapi_users.db import SQLAlchemyBaseOAuthAccountTableUUID
from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base
from .oauth_crypto import EncryptedToken


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    """Compte OAuth lié à un User.

    Colonnes héritées du mixin :
    - id (UUID PK)
    - oauth_name (str — "google")
    - expires_at (int Unix ts, nullable)
    - account_id (str — sub Google, stable)
    - account_email (str)

    Colonnes overridées :
    - user_id (FK vers `users.id`, pas `user.id`)
    - access_token (EncryptedToken au lieu de String)
    - refresh_token (EncryptedToken, nullable)
    """

    __tablename__ = "oauth_account"

    # Override : pointe sur notre table `users` (plural) au lieu du défaut `user`
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="cascade"),
        nullable=False,
    )

    # Override : tokens chiffrés au repos (cf ADR-014 §5)
    access_token: Mapped[str] = mapped_column(EncryptedToken, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(EncryptedToken, nullable=True)

    __table_args__ = (
        # Empêche qu'un même compte Google soit linké à 2 users Tangent
        UniqueConstraint(
            "oauth_name",
            "account_id",
            name="uq_oauth_account_provider_id",
        ),
    )
