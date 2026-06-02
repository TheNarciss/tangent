"""Routers OAuth Google — login + associate (cf ADR-014).

Deux routers exposés :
- build_google_login_router : /authorize + /callback pour signup/login (non loggé)
- build_google_associate_router : pour linker Google à un user déjà loggé

Sécurité critique : GoogleOAuth2Verified override get_id_email pour rejeter
toute réponse Google où email_verified=false. Sans ce check, un attaquant
pourrait créer un compte Google avec un email arbitraire non confirmé et
takeover un compte Tangent existant via associate_by_email.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.exceptions import GetIdEmailError

from . import fastapi_users
from .backend import auth_backend
from .schemas import UserRead

logger = logging.getLogger(__name__)


GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
OAUTH_STATE_SECRET = os.getenv("OAUTH_STATE_SECRET", "") or os.getenv("JWT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class GoogleOAuth2Verified(GoogleOAuth2):
    """GoogleOAuth2 qui rejette les emails non vérifiés (cf ADR-014 §4).

    Override get_id_email pour interroger l'endpoint OpenID userinfo (au lieu
    du people endpoint utilisé par défaut) et vérifier le flag email_verified.
    """

    OPENID_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

    async def get_id_email(self, token: str) -> tuple[str, str | None]:
        async with self.get_httpx_client() as client:
            response = await client.get(
                self.OPENID_USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code >= 400:
                logger.warning(
                    "Google userinfo fetch failed: status=%d body=%s",
                    response.status_code,
                    response.text[:200],
                )
                raise GetIdEmailError(response.text)

            data = response.json()
            email = data.get("email")
            if not data.get("email_verified", False):
                # Audit via stdlib logger : request context absent ici.
                logger.warning(
                    "AUDIT OAUTH_LINK_REJECTED_UNVERIFIED_EMAIL oauth_name=google email=%s",
                    email,
                )
                raise GetIdEmailError(
                    "Adresse email Google non vérifiée. Veuillez confirmer "
                    "votre adresse dans votre compte Google avant de vous "
                    "connecter à Tangent."
                )
            return data["sub"], email


def _missing_env() -> list[str]:
    return [
        name
        for name, val in [
            ("GOOGLE_OAUTH_CLIENT_ID", GOOGLE_OAUTH_CLIENT_ID),
            ("GOOGLE_OAUTH_CLIENT_SECRET", GOOGLE_OAUTH_CLIENT_SECRET),
            ("OAUTH_STATE_SECRET", OAUTH_STATE_SECRET),
            ("FRONTEND_URL", FRONTEND_URL),
        ]
        if not val
    ]


def is_oauth_configured() -> bool:
    """True ssi toutes les env vars OAuth sont définies."""
    return not _missing_env()


def _build_client() -> GoogleOAuth2Verified:
    missing = _missing_env()
    if missing:
        raise RuntimeError(
            f"OAuth Google config incomplete. Missing env vars: {', '.join(missing)}. "
            "Set them in backend/.env (cf ADR-014 §8)."
        )
    return GoogleOAuth2Verified(GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET)


def build_google_login_router() -> APIRouter:
    """Router /authorize + /callback pour signup/login Google (non loggé)."""
    client = _build_client()
    return fastapi_users.get_oauth_router(
        client,
        auth_backend,
        OAUTH_STATE_SECRET,
        # Google a déjà vérifié l'email (filtré par GoogleOAuth2Verified)
        # → marquer is_verified=True automatiquement
        is_verified_by_default=True,
        # Linker par email vérifié à un user existant (cf ADR-014 §4)
        associate_by_email=True,
    )


def build_google_associate_router() -> APIRouter:
    """Router /authorize + /callback pour linker Google à un user déjà loggé."""
    client = _build_client()
    return fastapi_users.get_oauth_associate_router(
        client,
        UserRead,
        OAUTH_STATE_SECRET,
        requires_verification=False,
    )
