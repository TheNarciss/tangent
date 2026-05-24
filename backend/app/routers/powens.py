"""Powens routes — per-user OAuth + sync (no more superuser hack).

Each authenticated user manages their own Powens token. The token is
identified via the tangent_auth cookie (SameSite=lax → sent on Powens
redirect to /auth/powens/callback).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db.engine import get_session
from ..db.models import PowensCredential
from ..powens import settings as powens_settings
from ..powens import state as powens_state
from ..powens.crypto import decrypt_token, encrypt_token
from ..powens.oauth import exchange_code_for_token
from ..powens.sync import sync_portfolio
from ..powens.webhooks import handle_webhook as powens_handle_webhook
from ..repositories import portfolio as portfolio_repo

logger = logging.getLogger(__name__)
router = APIRouter(tags=["powens"])


@router.get("/auth/powens/initiate")
async def get_powens_webview(user: User = Depends(current_active_user)):
    """Returns the URL the frontend must redirect to in order to start the Powens flow."""
    if not powens_settings.domain or not powens_settings.client_id:
        raise HTTPException(status_code=500, detail="Powens not configured.")
    redirect_uri = f"{powens_settings.backend_url}/auth/powens/callback"
    url = (
        f"https://{powens_settings.domain}/2.0/auth/webview/connect"
        f"?client_id={powens_settings.client_id}&redirect_uri={redirect_uri}"
    )
    return {"webview_url": url}


@router.get("/auth/powens/callback")
async def powens_auth_callback(
    code: str,
    user: User = Depends(current_active_user),  # ← identifies user via tangent_auth cookie
    connection_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """OAuth callback — exchange code for token and store it for THIS user.

    SameSite=lax allows the tangent_auth cookie to be sent on the Powens
    top-level redirect, so current_active_user works here.
    """
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

    # Upsert credential for THIS user (not "the first superuser")
    stmt = select(PowensCredential).where(PowensCredential.user_id == user.id)
    res = await session.execute(stmt)
    cred = res.scalars().first()
    if cred:
        cred.encrypted_token = encrypt_token(access_token)
        logger.info("Updated Powens token for user_id=%s", user.id)
    else:
        cred = PowensCredential(
            user_id=user.id,
            encrypted_token=encrypt_token(access_token),
        )
        session.add(cred)
        logger.info("Stored new Powens token for user_id=%s", user.id)
    await session.commit()

    return RedirectResponse(url=f"{powens_settings.frontend_url}/?powens_sync=success")


@router.post("/sync/powens")
async def post_sync_powens(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Trigger a sync for the current user (no superuser required)."""
    stmt = select(PowensCredential).where(PowensCredential.user_id == user.id)
    res = await session.execute(stmt)
    cred = res.scalars().first()

    if not cred:
        raise HTTPException(
            status_code=400,
            detail="No Powens connection. Click 'Connect Powens' first.",
        )

    # TODO Phase 5 proper: pass token to sync_portfolio(user_id, token) directly.
    # For now: temporarily inject into global settings (still mono-user under the hood).
    powens_settings.user_token = decrypt_token(cred.encrypted_token)

    result = await sync_portfolio()

    # Persist positions to DB for THIS user (multi-tenant)
    if result.success and result.positions:
        positions_data = [p.model_dump() for p in result.positions]
        await portfolio_repo.replace_positions(
            session,
            user.id,
            new_positions=positions_data,
            cash=result.cash_balance,
        )
        logger.info("Persisted %d positions to DB for user_id=%s", len(result.positions), user.id)

    return result


@router.get("/sync/status")
async def get_sync_status(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Status of the user's Powens connection + last sync."""
    stmt = select(PowensCredential).where(PowensCredential.user_id == user.id)
    res = await session.execute(stmt)
    has_cred = res.scalars().first() is not None

    st = powens_state.load()
    return {
        "configured": powens_settings.is_configured,
        "user_connected": has_cred,
        "last_sync": st.last_sync.isoformat() if st.last_sync else None,
        "last_webhook": st.last_webhook.isoformat() if st.last_webhook else None,
        "last_error": st.last_error,
        "age_hours": st.age_hours,
        "positions_count": st.positions_count,
        "cash_balance": st.cash_balance,
        "is_stale": powens_state.is_stale(),
    }


@router.post("/webhooks/powens")
async def post_webhook_powens(payload: dict):
    """Powens webhooks (CONNECTION_SYNCED, etc.). No auth — Powens-to-server."""
    return await powens_handle_webhook(payload)
