"""Powens routes — per-user OAuth + sync (multi-tenant safe).

Each authenticated user manages their own Powens token. All sync state
(last_sync_at, last_error, etc.) is persisted per-user in PowensCredential.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db.engine import get_session
from ..db.models import PowensCredential
from ..powens import settings as powens_settings
from ..powens.client import PowensClient, PowensError
from ..powens.crypto import decrypt_token, encrypt_token
from ..powens.oauth import exchange_code_for_token
from ..powens.webhooks import handle_webhook as powens_handle_webhook

logger = logging.getLogger(__name__)
# Router for /sync/* — namespaced under /api/* via main.py include_router(..., prefix="/api")
router = APIRouter(tags=["sync"])

# Legacy router for Powens-specific external callbacks (ADR-020 exception):
# - /auth/powens/initiate, /auth/powens/callback (Powens sandbox = single redirect URI)
# - /webhooks/powens (external Powens POST, currently disabled per ADR-019)
# Mounted WITHOUT /api prefix in main.py to match Powens dashboard config.
legacy_router = APIRouter(tags=["powens-legacy"])


@legacy_router.get("/auth/powens/initiate")
async def get_powens_webview(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Returns the Powens webview URL to start an "Add bank" flow.

    Critical: if the user already has a Powens credential (= already linked
    at least one bank), we MUST generate a temporary_code scoped to that user
    and pass it in the URL. Without it, Powens creates a NEW anonymous user
    on every webview load, which orphans the previous bank (cf bug post-OAuth).

    Behavior:
    - First-ever bank: no code → Powens creates the Tangent user's Powens user.
    - Subsequent banks: code = single-access temp code scoped to existing user.
    """
    if not powens_settings.domain or not powens_settings.client_id:
        raise HTTPException(status_code=500, detail="Powens not configured.")

    redirect_uri = f"{powens_settings.backend_url}/auth/powens/callback"
    base_url = (
        f"https://{powens_settings.domain}/2.0/auth/webview/connect"
        f"?client_id={powens_settings.client_id}&redirect_uri={redirect_uri}"
    )

    # If a credential already exists, generate a temp code to ADD a new
    # connection to the same Powens user (instead of creating a fresh one).
    stmt = select(PowensCredential).where(PowensCredential.user_id == user.id)
    res = await session.execute(stmt)
    cred = res.scalars().first()

    if cred is None:
        logger.info("Powens initiate user=%s: first-time connect (no temp code)", user.id)
        return {"webview_url": base_url}

    try:
        token = decrypt_token(cred.encrypted_token)
        async with PowensClient(token=token) as client:
            temp_code = await client.get_temporary_code()
    except PowensError:
        # Token might be revoked or invalid — fall back to fresh user.
        # The new user will replace this credential at callback.
        logger.exception(
            "Powens initiate user=%s: temp code generation failed, falling back to fresh user flow",
            user.id,
        )
        return {"webview_url": base_url}

    logger.info("Powens initiate user=%s: adding bank to existing Powens user", user.id)
    return {"webview_url": f"{base_url}&code={temp_code}"}


@legacy_router.get("/auth/powens/callback")
async def powens_auth_callback(
    user: User = Depends(current_active_user),
    code: str | None = None,
    connection_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """OAuth callback — handles both first-time connect and "add another bank".

    Powens behavior (cf webview /connect doc):
    - First time (no code sent to webview): callback receives a `code` that we
      must exchange for a permanent access_token. We persist it.
    - Subsequent times (we sent code=<temp> to webview): callback has NO code
      because the existing token already covers the new connection. Nothing
      to persist; we just confirm to the frontend.
    """
    # Case 2: adding a bank to existing Powens user — no new token to store
    if code is None:
        logger.info(
            "Powens callback user=%s: connection added to existing user (connection_id=%s)",
            user.id,
            connection_id,
        )
        return RedirectResponse(url=f"{powens_settings.frontend_url}/?powens_sync=success")

    # Case 1: first-time connect — exchange code → token, store credential
    try:
        token_data = await exchange_code_for_token(code)
    except Exception:
        logger.exception("Powens token exchange failed for user %s", user.id)
        return RedirectResponse(
            url=f"{powens_settings.frontend_url}/?powens_sync=error&error=token_exchange_failed"
        )

    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse(
            url=f"{powens_settings.frontend_url}/?powens_sync=error&error=no_access_token"
        )

    stmt = select(PowensCredential).where(PowensCredential.user_id == user.id)
    res = await session.execute(stmt)
    cred = res.scalars().first()
    if cred:
        # Should not normally happen now (temp_code path used instead), but
        # defensive: replace token if somehow we end up here.
        cred.encrypted_token = encrypt_token(access_token)
        logger.warning(
            "Powens callback user=%s: replacing existing token (unexpected — "
            "temp_code path should have been used)",
            user.id,
        )
    else:
        cred = PowensCredential(
            user_id=user.id,
            encrypted_token=encrypt_token(access_token),
        )
        session.add(cred)
        logger.info("Stored initial Powens token for user_id=%s", user.id)
    await session.commit()

    return RedirectResponse(url=f"{powens_settings.frontend_url}/?powens_sync=success")


@router.get("/sync/status")
async def get_sync_status(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Status of the user's Powens connection + last sync (per-user, from DB)."""
    stmt = select(PowensCredential).where(PowensCredential.user_id == user.id)
    res = await session.execute(stmt)
    cred = res.scalars().first()

    if cred is None:
        return {
            "configured": powens_settings.is_configured,
            "user_connected": False,
            "last_sync": None,
            "last_webhook": None,
            "last_error": None,
            "age_hours": None,
            "positions_count": 0,
            "cash_balance": 0.0,
            "is_stale": False,
        }

    age_hours: float | None = None
    if cred.last_sync_at:
        age_hours = (datetime.now(UTC) - cred.last_sync_at).total_seconds() / 3600

    is_stale = age_hours is None or age_hours > powens_settings.autosync_threshold_hours

    return {
        "configured": powens_settings.is_configured,
        "user_connected": True,
        "last_sync": cred.last_sync_at.isoformat() if cred.last_sync_at else None,
        "last_webhook": cred.last_webhook_at.isoformat() if cred.last_webhook_at else None,
        "last_error": cred.last_error,
        "age_hours": age_hours,
        "positions_count": cred.last_positions_count,
        "cash_balance": cred.last_cash_balance,
        "is_stale": is_stale,
    }


@legacy_router.post("/webhooks/powens")
async def post_webhook_powens(payload: dict):
    """Powens webhooks — handler disabled until Phase A per-user mapping."""
    return await powens_handle_webhook(payload)
