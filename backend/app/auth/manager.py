"""UserManager FastAPI-Users — handlers register/login/oauth/reset-password/etc.

Configure :
- Argon2 comme password hashing (recommandé OWASP 2026)
- Validations custom (mot de passe min 8 chars, email pas pris)
- Hooks après register/login/oauth (audit logs)
"""

import logging
import os
import uuid

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin, exceptions
from fastapi_users.password import PasswordHelper
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from .models import User
from .oauth_models import OAuthAccount
from .schemas import UserCreate

logger = logging.getLogger(__name__)


# Argon2 password hashing — plus moderne que bcrypt, recommandé OWASP
_password_hash = PasswordHash((Argon2Hasher(),))
_password_helper = PasswordHelper(_password_hash)


# User.hashed_password nullable (ADR-014) — runtime safe, mais viole UserProtocol
class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):  # type: ignore[type-var]
    """Logique métier des users — appelée par les routes /auth/*."""

    # Secrets pour signer les tokens de reset password + email verification.
    reset_password_token_secret = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
    verification_token_secret = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")

    # ── Validations custom au moment du register ──

    async def validate_password(  # type: ignore[override]
        self, password: str, user: UserCreate | User
    ) -> None:
        """Règles de mot de passe (silently log, raise InvalidPasswordException si KO)."""
        if len(password) < 8:
            raise exceptions.InvalidPasswordException(
                reason="Le mot de passe doit faire au moins 8 caractères."
            )

    # ── Hooks classiques ──

    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        from .audit import log_event

        log_event(
            "AUTH_REGISTER",
            user_id=str(user.id),
            ip=request.client.host if request and request.client else None,
        )

    async def on_after_login(
        self, user: User, request: Request | None = None, response=None
    ) -> None:
        from .audit import log_event

        log_event(
            "AUTH_LOGIN_SUCCESS",
            user_id=str(user.id),
            ip=request.client.host if request and request.client else None,
        )

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        from .audit import log_event

        log_event(
            "AUTH_PASSWORD_RESET_REQUEST",
            user_id=str(user.id),
            ip=request.client.host if request and request.client else None,
        )

    async def on_after_reset_password(self, user: User, request: Request | None = None) -> None:
        from .audit import log_event

        log_event(
            "AUTH_PASSWORD_RESET_CONFIRM",
            user_id=str(user.id),
            ip=request.client.host if request and request.client else None,
        )

    async def on_after_request_verify(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        # Token sent via email only — never logged.
        pass

    # ── OAuth hooks (cf ADR-014) ──

    async def oauth_callback(
        self,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: str,
        expires_at: int | None = None,
        refresh_token: str | None = None,
        request: Request | None = None,
        *,
        associate_by_email: bool = False,
        is_verified_by_default: bool = False,
    ) -> User:
        """Override pour audit log + détection new-vs-existing.

        Note : la validation email_verified=true est faite plus tôt dans
        GoogleOAuth2Verified.get_id_email — si l'email n'est pas vérifié, on
        n'arrive jamais ici (cf ADR-014 §4).
        """
        from .audit import log_event

        # Détecter new user vs link existant AVANT l'appel parent
        existing = await self.user_db.get_by_email(account_email)
        is_new_user = existing is None

        user = await super().oauth_callback(
            oauth_name,
            access_token,
            account_id,
            account_email,
            expires_at,
            refresh_token,
            request,
            associate_by_email=associate_by_email,
            is_verified_by_default=is_verified_by_default,
        )

        ip = request.client.host if request and request.client else None
        event = "OAUTH_REGISTER" if is_new_user else "OAUTH_LOGIN_SUCCESS"
        log_event(
            event,
            user_id=str(user.id),
            oauth_name=oauth_name,
            ip=ip,
        )
        return user

    async def on_after_update(
        self, user: User, update_dict: dict, request: Request | None = None
    ) -> None:
        # Hook réservé pour audit futur
        pass


async def get_user_db(session: AsyncSession = Depends(get_session)):
    """Dependency : injecte la couche d'accès DB pour users + oauth_accounts."""
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)


async def get_user_manager(user_db=Depends(get_user_db)):
    """Dependency : injecte le UserManager dans les endpoints."""
    yield UserManager(user_db, password_helper=_password_helper)
