"""HTTP client for the Enable Banking API.

Every call carries a short-lived JWT signed with the application's RSA key
(RS256, `kid` = application id). Errors surface as `EnableBankingError`
with the API's own message, so a route can show the user what happened.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any

import httpx
import jwt

from . import settings

logger = logging.getLogger(__name__)

_MAX_PAGES = 100  # transactions are paged; a personal account never needs more


class EnableBankingError(Exception):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def bearer_token(*, app_id: str, private_key_pem: str, ttl_seconds: int = 3600) -> str:
    """The JWT Enable Banking expects: issuer and audience fixed, one hour of life."""
    now = int(time.time())
    return jwt.encode(
        {
            "iss": "enablebanking.com",
            "aud": "api.enablebanking.com",
            "iat": now,
            "exp": now + ttl_seconds,
        },
        private_key_pem,
        algorithm="RS256",
        headers={"kid": app_id},
    )


class EnableBankingClient:
    def __init__(
        self,
        *,
        app_id: str | None = None,
        private_key_pem: str | None = None,
        base_url: str | None = None,
    ) -> None:
        token = bearer_token(
            app_id=app_id or settings.app_id,
            private_key_pem=private_key_pem or settings.private_key_pem,
        )
        self._client = httpx.AsyncClient(
            base_url=base_url or settings.base_url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30.0,
        )

    async def __aenter__(self) -> EnableBankingClient:
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise EnableBankingError(f"Enable Banking injoignable: {exc}") from exc
        if response.status_code >= 400:
            detail: str
            try:
                body = response.json()
                detail = str(body.get("message") or body.get("error") or body)
            except ValueError:
                detail = response.text[:200]
            raise EnableBankingError(
                f"Enable Banking a répondu {response.status_code}: {detail}",
                status=response.status_code,
            )
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise EnableBankingError("Réponse non-JSON d'Enable Banking.") from exc

    # ── Banks and authorisation ────────────────────────────────────────────

    async def list_banks(self, country: str, psu_type: str = "personal") -> list[dict]:
        data = await self._request(
            "GET", "/aspsps", params={"country": country, "psu_type": psu_type}
        )
        return list(data.get("aspsps") or [])

    async def start_authorization(
        self,
        *,
        bank_name: str,
        country: str,
        psu_type: str,
        redirect_url: str,
        state: str,
        valid_until: datetime,
    ) -> dict:
        """Returns {url, authorization_id}; the user goes to `url` to consent at the bank."""
        return await self._request(
            "POST",
            "/auth",
            json={
                "access": {"valid_until": valid_until.isoformat()},
                "aspsp": {"name": bank_name, "country": country},
                "state": state,
                "redirect_url": redirect_url,
                "psu_type": psu_type,
            },
        )

    async def create_session(self, code: str) -> dict:
        """Turns the code from the redirect into a session: {session_id, accounts, access, aspsp}."""
        return await self._request("POST", "/sessions", json={"code": code})

    async def get_session(self, session_id: str) -> dict:
        return await self._request("GET", f"/sessions/{session_id}")

    async def delete_session(self, session_id: str) -> None:
        await self._request("DELETE", f"/sessions/{session_id}")

    # ── Account data ───────────────────────────────────────────────────────

    async def get_account_details(self, account_uid: str) -> dict:
        """Name, currency, type, IBAN: a session only lists uids."""
        return await self._request("GET", f"/accounts/{account_uid}/details")

    async def get_balances(self, account_uid: str) -> list[dict]:
        data = await self._request("GET", f"/accounts/{account_uid}/balances")
        return list(data.get("balances") or [])

    async def get_transactions(
        self, account_uid: str, *, date_from: date | None = None, date_to: date | None = None
    ) -> list[dict]:
        """Every transaction in the window, following continuation keys."""
        params: dict[str, str] = {}
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        out: list[dict] = []
        for _ in range(_MAX_PAGES):
            data = await self._request(
                "GET", f"/accounts/{account_uid}/transactions", params=params
            )
            out.extend(data.get("transactions") or [])
            key = data.get("continuation_key")
            if not key:
                break
            params["continuation_key"] = str(key)
        return out
