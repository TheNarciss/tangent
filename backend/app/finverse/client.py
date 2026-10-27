"""HTTP client for the Finverse Data API.

Two kinds of bearer token. The customer token (client credentials, an hour
of life) creates links, exchanges codes and refreshes tokens. A login
identity token reads one person's linked bank: accounts, transactions.
Errors surface as `FinverseError` with the API's own message.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from . import settings

logger = logging.getLogger(__name__)

PAGE_SIZE = 500  # transactions per call; Finverse allows up to 1000
MAX_TRANSACTIONS = 5000  # a personal account never needs more in one read


class FinverseError(Exception):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def _reason(body: Any) -> str:
    """Finverse's own words: the specific `details` when it gives them, its code, its message.

    « The parameters provided are invalid. See details. » alone says nothing:
    the reason is in `details` (« client_secret … at least 64 chars long »).
    """
    if not isinstance(body, dict):
        return str(body)[:200]
    raw = body.get("error")
    error: dict = raw if isinstance(raw, dict) else {}
    code = error.get("error_code") or error.get("code")
    words = error.get("details") or body.get("message") or error.get("message") or body
    return f"{code}: {words}" if code else str(words)


class FinverseClient:
    def __init__(self, *, base_url: str | None = None) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url or settings.base_url,
            headers={"Accept": "application/json"},
            timeout=30.0,
        )
        self._customer_token: str | None = None

    async def __aenter__(self) -> FinverseClient:
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, token: str | None, **kwargs: Any) -> Any:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            response = await self._client.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise FinverseError(f"Finverse injoignable: {exc}") from exc
        if response.status_code >= 400:
            try:
                detail = _reason(response.json())
            except ValueError:
                detail = response.text[:200]
            raise FinverseError(
                f"Finverse a répondu {response.status_code}: {detail}",
                status=response.status_code,
            )
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise FinverseError("Réponse non-JSON de Finverse.") from exc

    async def _customer(self) -> str:
        """The application's own token, asked once per client."""
        if self._customer_token is None:
            data = await self._request(
                "POST",
                "/auth/customer/token",
                None,
                json={
                    "client_id": settings.client_id,
                    "client_secret": settings.client_secret,
                    "grant_type": "client_credentials",
                },
            )
            self._customer_token = str(data["access_token"])
        return self._customer_token

    # ── Linking ────────────────────────────────────────────────────────────

    async def link_url(self, *, user_ref: str, state: str) -> str:
        """Where Finverse Link opens; it posts the code back to the redirect URI."""
        data = await self._request(
            "POST",
            "/link/token",
            await self._customer(),
            json={
                "client_id": settings.client_id,
                "user_id": user_ref,
                "redirect_uri": settings.redirect_uri,
                "state": state,
                "grant_type": "client_credentials",
                "response_type": "code",
                "response_mode": "form_post",
                "ui_mode": "redirect",
                "automatic_data_refresh": "ON",
            },
        )
        return str(data["link_url"])

    async def exchange(self, code: str) -> dict:
        """Code → login identity token, its refresh token and the login identity id."""
        return dict(
            await self._request(
                "POST",
                "/auth/token",
                await self._customer(),
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.client_id,
                    "redirect_uri": settings.redirect_uri,
                },
            )
        )

    async def refresh(self, refresh_token: str) -> dict:
        """A fresh login identity token; the answer may carry a new refresh token."""
        return dict(
            await self._request(
                "POST",
                "/auth/token/refresh",
                await self._customer(),
                json={"refresh_token": refresh_token},
            )
        )

    # ── One person's data ──────────────────────────────────────────────────

    async def login_identity(self, token: str) -> dict:
        """The link itself: its status tells whether the bank has been read."""
        return dict(await self._request("GET", "/login_identity", token))

    async def accounts(self, token: str) -> dict:
        return dict(await self._request("GET", "/accounts", token))

    async def transactions(self, token: str) -> list[dict]:
        """Every transaction, most recent first, page after page."""
        out: list[dict] = []
        while len(out) < MAX_TRANSACTIONS:
            data = await self._request(
                "GET", "/transactions", token, params={"offset": len(out), "limit": PAGE_SIZE}
            )
            page = list(data.get("transactions") or [])
            out.extend(page)
            if not page or len(out) >= int(data.get("total_transactions") or 0):
                break
        return out

    async def unlink(self, token: str) -> None:
        await self._request("DELETE", "/login_identity", token)
