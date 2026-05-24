"""Powens OAuth — exchange authorization code for an access token."""
import logging

import httpx

from . import settings

logger = logging.getLogger(__name__)


async def exchange_code_for_token(code: str) -> dict:
    """Exchange the authorization code returned by Powens webview for a permanent
    access token bound to the user.

    Powens spec: POST https://{domain}/2.0/auth/token/access
        Body (form-encoded):
            client_id, client_secret, code
        Response:
            {"access_token": "...", "type": "permanent_user_token"}
    """
    if not settings.client_id or not settings.client_secret:
        raise ValueError("POWENS_CLIENT_ID or POWENS_CLIENT_SECRET missing in .env")

    url = f"{settings.base_url}/auth/token/access"
    payload = {
        "client_id": settings.client_id,
        "client_secret": settings.client_secret,
        "code": code,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, data=payload)
        logger.info("Powens token exchange: status=%d", response.status_code)

        if response.status_code != 200:
            raise RuntimeError(
                f"Powens token exchange failed: {response.status_code} — {response.text[:200]}"
            )
        return response.json()
