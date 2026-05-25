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
    user: User = Depends(current_active_user),
    connection_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """OAuth callback — exchange code for token and store it for THIS user."""
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
    """Trigger a Powens sync for the current user (multi-tenant safe)."""
    stmt = select(PowensCredential).where(PowensCredential.user_id == user.id)
    res = await session.execute(stmt)
    cred = res.scalars().first()

    if not cred:
        raise HTTPException(
            status_code=400,
            detail="No Powens connection. Click 'Connect Powens' first.",
        )

    token = decrypt_token(cred.encrypted_token)

    result = await sync_portfolio(
        token=token,
        user_id=user.id,
        session=session,
    )

    if result.success and result.positions:
        positions_data = [p.model_dump() for p in result.positions]
        await portfolio_repo.replace_positions(
            session,
            user.id,
            new_positions=positions_data,
            cash=result.cash_balance,
        )
        logger.info(
            "Persisted %d positions to DB for user_id=%s",
            len(result.positions),
            user.id,
        )

    return result


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


@router.post("/webhooks/powens")
async def post_webhook_powens(payload: dict):
    """Powens webhooks — handler disabled until Phase A per-user mapping."""
    return await powens_handle_webhook(payload)
