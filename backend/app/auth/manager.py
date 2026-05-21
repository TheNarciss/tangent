"""UserManager FastAPI-Users — handlers register/login/reset-password/etc.

Configure :
- Argon2 comme password hashing (recommandé OWASP 2026)
- Validations custom (mot de passe min 8 chars, email pas pris)
- Hooks après register/login (logs, futures notifs email)
"""
import logging
import os
import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, exceptions
from fastapi_users.password import PasswordHelper
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from .models import User
from .schemas import UserCreate

logger = logging.getLogger(__name__)


# Argon2 password hashing — plus moderne que bcrypt, recommandé OWASP
_password_hash = PasswordHash((Argon2Hasher(),))
_password_helper = PasswordHelper(_password_hash)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Logique métier des users — appelée par les routes /auth/*."""

    # Secrets pour signer les tokens de reset password + email verification.
    # On utilise le même JWT_SECRET que le backend auth (= défini en env).
    reset_password_token_secret = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
    verification_token_secret = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")

    # ── Validations custom au moment du register ──

    async def validate_password(self, password: str, user: UserCreate | User) -> None:
        """Règles de mot de passe (silently log, raise InvalidPasswordException si KO)."""
        if len(password) < 8:
            raise exceptions.InvalidPasswordException(
                reason="Le mot de passe doit faire au moins 8 caractères."
            )
        # Possible : ajouter des checks plus stricts (majuscule, chiffre, etc.)
        # On reste laxiste pour un projet perso — l'argon2 hashing compense.

    # ── Hooks ──

    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        from .audit import log_event
        log_event(
            "AUTH_REGISTER",
            user_id=str(user.id),
            email=user.email,
            ip=request.client.host if request and request.client else None,
        )

    async def on_after_login(self, user: User, request: Request | None = None, response=None) -> None:
        from .audit import log_event
        log_event(
            "AUTH_LOGIN_SUCCESS",
            user_id=str(user.id),
            email=user.email,
            ip=request.client.host if request and request.client else None,
        )

    async def on_after_forgot_password(self, user: User, token: str, request: Request | None = None) -> None:
        from .audit import log_event
        log_event(
            "AUTH_PASSWORD_RESET_REQUEST",
            user_id=str(user.id),
            email=user.email,
            ip=request.client.host if request and request.client else None,
        )
        # ⚠️ En DEV seulement : on log le token pour pouvoir reset sans SMTP.
        # En prod, à envoyer par email uniquement. APP_ENV doit valoir "dev" dans .env.
        if os.getenv("APP_ENV", "dev").lower() == "dev":
            logger.info("[DEV] Password reset token for user=%s: %s", user.id, token)

    async def on_after_reset_password(self, user: User, request: Request | None = None) -> None:
        from .audit import log_event
        log_event(
            "AUTH_PASSWORD_RESET_CONFIRM",
            user_id=str(user.id),
            email=user.email,
            ip=request.client.host if request and request.client else None,
        )

    async def on_after_request_verify(self, user: User, token: str, request: Request | None = None) -> None:
        if os.getenv("APP_ENV", "dev").lower() == "dev":
            logger.info("[DEV] Verification token for user=%s: %s", user.id, token)


async def get_user_db(session: AsyncSession = Depends(get_session)):
    """Dependency : injecte la couche d'accès DB pour les users."""
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(user_db=Depends(get_user_db)):
    """Dependency : injecte le UserManager dans les endpoints."""
    yield UserManager(user_db, password_helper=_password_helper)