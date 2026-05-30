"""Client HTTP async pour l'API Powens.

Wrapper minimal autour de httpx avec :
- Auth Bearer per-user (token passé en paramètre, plus de global state)
- Retry léger sur 5xx (max 2 retries)
- Timeout configurable
- Exceptions explicites (PowensAuthError vs PowensConnectorError vs PowensConflictError)
"""

import asyncio
import logging
from typing import Any

import httpx

from . import settings, yaml_config

logger = logging.getLogger(__name__)


class PowensError(Exception):
    """Base class pour les erreurs Powens."""


class PowensAuthError(PowensError):
    """401 — token invalide ou expiré, l'utilisateur doit ré-auth."""


class PowensConnectorError(PowensError):
    """Erreur côté connecteur BNP/etc. (404, 409 sur certaines routes)."""


class PowensConflictError(PowensError):
    """409 — opération en cours, ex: sync déjà en cours."""


class PowensClient:
    """Client minimaliste pour /users/me/* endpoints (multi-tenant safe).

    Le token est passé en paramètre, jamais lu depuis un global. Chaque user
    Tangent a son propre token chiffré en DB.

    Usage :
        async with PowensClient(token=user_token) as client:
            accounts = await client.get_accounts()
    """

    def __init__(self, token: str) -> None:
        if not settings.domain:
            raise PowensError("Powens not configured: POWENS_DOMAIN missing in .env")
        if not token:
            raise PowensError("PowensClient requires a non-empty token")
        self.base_url = settings.base_url
        self.token = token
        timeout = yaml_config.get("request_timeout_seconds", 30)
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=timeout,
        )

    async def __aenter__(self) -> "PowensClient":
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        """Wrapper avec retry simple sur 5xx + mapping d'erreurs."""
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._client.request(method, path, **kwargs)
                if response.status_code == 401:
                    raise PowensAuthError(
                        "Powens 401: token expired or invalid. User must re-OAuth."
                    )
                if response.status_code == 409:
                    raise PowensConflictError(f"Powens 409 sur {path} : {response.text[:200]}")
                if response.status_code == 404:
                    raise PowensConnectorError(f"Powens 404 sur {path} — ressource introuvable.")
                if response.status_code >= 500:
                    last_exc = PowensError(f"Powens {response.status_code} sur {path}")
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning("Powens timeout (tentative %d) sur %s", attempt + 1, path)
                await asyncio.sleep(0.5 * (attempt + 1))
            except (PowensAuthError, PowensConflictError, PowensConnectorError):
                raise
        raise PowensError(f"Powens unreachable après 3 tentatives : {last_exc}")

    # ── Endpoints publics ───────────────────────────────────────────────────

    async def get_me(self) -> dict:
        return await self._request("GET", "/users/me")

    async def get_connections(self) -> list[dict]:
        data = await self._request("GET", "/users/me/connections?expand=connector,bank")
        return data.get("connections", [])

    async def get_accounts(self) -> list[dict]:
        data = await self._request("GET", "/users/me/accounts")
        return data.get("accounts", [])

    async def get_investments(self, account_id: int) -> list[dict]:
        data = await self._request("GET", f"/users/me/accounts/{account_id}/investments")
        return data.get("investments", [])

    async def get_transactions(self, account_id: int, limit: int = 100) -> list[dict]:
        data = await self._request(
            "GET",
            f"/users/me/accounts/{account_id}/transactions",
            params={"limit": limit},
        )
        return data.get("transactions", [])

    async def get_marketorders(self, account_id: int) -> list[dict]:
        data = await self._request("GET", f"/users/me/accounts/{account_id}/marketorders")
        return data.get("marketorders", [])

    async def force_sync(self, connection_id: int) -> dict:
        """Force une re-sync d'une connexion. Peut renvoyer 409 si une sync est en cours."""
        return await self._request("PUT", f"/users/me/connections/{connection_id}")

    async def get_temporary_code(self) -> str:
        """Generate a short-lived single-access code scoped to the current user.

        Used to add a new connection (via webview) to THIS Powens user instead
        of creating a fresh anonymous user. The code expires in 30 minutes.
        Returns the raw code string (already URL-safe per Powens contract).
        """
        data = await self._request("GET", "/auth/token/code", params={"type": "singleAccess"})
        code = data.get("code")
        if not isinstance(code, str) or not code:
            raise PowensError("Powens /auth/token/code returned no code")
        return code
