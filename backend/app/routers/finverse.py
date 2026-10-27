"""Finverse routes — connect an Asian bank (DBS, POSB, OCBC…) (ADR-037).

Same shape as Enable Banking: a callback outside /api because its URL is
registered in Finverse's dashboard, everything else under /api/finverse.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..aggregator.persist import persist_sync_result
from ..auth import User, current_active_user, current_active_user_optional
from ..auth import session as app_session
from ..db.engine import get_session
from ..db.models import BankAccount, FinverseConnection
from ..errors import UPSTREAM_DOWN
from ..finverse import settings
from ..finverse.aggregator import PROVIDER, read, wait_for_data
from ..finverse.client import FinverseClient, FinverseError
from ..i18n import Locale, current_locale, t
from ..powens.crypto import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finverse", tags=["finverse"])
legacy_router = APIRouter(tags=["finverse-callback"])

_STATE_SECRET = os.getenv("OAUTH_STATE_SECRET", "") or os.getenv("JWT_SECRET", "")
_STATE_TTL = timedelta(minutes=30)


class LinkIn(BaseModel):
    platform: Literal["web", "app"] = "web"  # the app returns to tangent://banks (ADR-035)


class LinkOut(BaseModel):
    url: str


class ConnectionOut(BaseModel):
    id: uuid.UUID
    institution_name: str
    accounts_count: int
    last_sync_at: datetime | None
    last_error: str | None


@router.get("/status")
async def status(user: User = Depends(current_active_user)) -> dict[str, bool]:
    return {"configured": settings.is_configured}


@router.post("/link", response_model=LinkOut)
async def link(
    body: LinkIn,
    user: User = Depends(current_active_user),
    locale: Locale = Depends(current_locale),
) -> LinkOut:
    """Where Finverse Link opens: the person picks their bank and logs in there."""
    if not settings.is_configured:
        raise HTTPException(status_code=503, detail=t(locale, "errors.finverse_not_configured"))
    try:
        async with FinverseClient() as client:
            url = await client.link_url(
                user_ref=str(user.id), state=_sign_state(user.id, body.platform)
            )
    except FinverseError as exc:
        logger.warning("Finverse link user=%s: %s", user.id, exc)
        raise HTTPException(status_code=UPSTREAM_DOWN, detail=str(exc)) from exc
    return LinkOut(url=url)


@legacy_router.api_route("/auth/finverse/callback", methods=["GET", "POST"])
async def callback(
    request: Request,
    cookie_user: User | None = Depends(current_active_user_optional),
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """Finverse Link is done: keep the refresh token, read the bank once.

    Finverse posts the code from its own domain, so no session cookie comes
    with it (SameSite=Lax): the signed state alone says who started the flow.
    A cookie that names someone else still stops it.
    """
    fields = dict(request.query_params)
    if request.method == "POST":
        fields.update({k: str(v) for k, v in (await request.form()).items()})
    try:
        claims = _read_state(fields.get("state", ""))
    except jwt.PyJWTError:
        return _back("error&error=bad_state")
    platform = str(claims.get("platform", "web"))
    code = fields.get("code")
    if fields.get("error") or not code:
        return _back(f"error&error={_slug(fields.get('error') or 'no_code')}", platform)
    if cookie_user is not None and claims.get("sub") != str(cookie_user.id):
        return _back("error&error=wrong_user", platform)
    user = await db.get(User, uuid.UUID(str(claims["sub"])))
    if user is None or not user.is_active:
        return _back("error&error=wrong_user", platform)

    try:
        async with FinverseClient() as client:
            tokens = await client.exchange(code)
            token = str(tokens["access_token"])
            login_identity_id = str(tokens["login_identity_id"])[:64]
            encrypted = encrypt_token(str(tokens["refresh_token"]))
            status = await wait_for_data(client, token)
            # One row per linked login: linking the same bank again replaces
            # its token, its accounts keep their identity and their history.
            row = (
                (
                    await db.execute(
                        select(FinverseConnection)
                        .where(FinverseConnection.user_id == user.id)
                        .where(FinverseConnection.login_identity_id == login_identity_id)
                    )
                )
                .scalars()
                .first()
            )
            if row is None:
                row = FinverseConnection(user_id=user.id, login_identity_id=login_identity_id)
                db.add(row)
            row.encrypted_refresh_token = encrypted
            row.last_error = None if status != "ERROR" else "Finverse n'a pas pu lire la banque."
            await db.commit()
            await db.refresh(row)
            if status == "ERROR":
                return _back("error&error=bank_read", platform)
            # The link is stored whatever happens next: a failed first read
            # shows on the row, it does not cost the user another login.
            try:
                result = await read(client, token, row)
                await persist_sync_result(db, user.id, result)
                row.last_sync_at = result.synced_at
            except Exception as exc:
                logger.exception("Finverse: première relève en échec pour user=%s", user.id)
                row.last_error = f"{type(exc).__name__}: {exc}"[:500]
            await db.commit()
    except (FinverseError, KeyError) as exc:
        logger.warning("Finverse callback user=%s: %s", user.id, exc)
        return _back("error&error=exchange", platform)
    except ValueError:
        return _back("error&error=encryption_not_configured", platform)
    return _back("success", platform)


@router.get("/connections", response_model=list[ConnectionOut])
async def connections(
    user: User = Depends(current_active_user), db: AsyncSession = Depends(get_session)
) -> list[ConnectionOut]:
    rows = (
        (
            await db.execute(
                select(FinverseConnection)
                .where(FinverseConnection.user_id == user.id)
                .order_by(FinverseConnection.created_at)
            )
        )
        .scalars()
        .all()
    )
    out: list[ConnectionOut] = []
    for row in rows:
        count = await db.scalar(
            select(func.count())
            .select_from(BankAccount)
            .where(BankAccount.user_id == user.id)
            .where(BankAccount.provider == PROVIDER)
            .where(BankAccount.raw_data["finverse_connection"].astext == str(row.id))
        )
        out.append(
            ConnectionOut(
                id=row.id,
                institution_name=row.institution_name,
                accounts_count=int(count or 0),
                last_sync_at=row.last_sync_at,
                last_error=row.last_error,
            )
        )
    return out


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: uuid.UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    """Unlink at Finverse (best effort), then drop the row and its accounts."""
    row = await db.get(FinverseConnection, connection_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Connexion inconnue.")
    await _unlink(row)
    accounts = (
        (
            await db.execute(
                select(BankAccount)
                .where(BankAccount.user_id == user.id)
                .where(BankAccount.provider == PROVIDER)
                .where(BankAccount.raw_data["finverse_connection"].astext == str(row.id))
            )
        )
        .scalars()
        .all()
    )
    for acc in accounts:
        await db.delete(acc)
    await db.delete(row)
    await db.commit()


# ── helpers ────────────────────────────────────────────────────────────────


async def _unlink(row: FinverseConnection) -> None:
    """Best effort: end the link at Finverse; a failure is only logged."""
    try:
        async with FinverseClient() as client:
            tokens = await client.refresh(decrypt_token(row.encrypted_refresh_token))
            await client.unlink(str(tokens["access_token"]))
    except (FinverseError, KeyError, ValueError) as exc:
        logger.warning("Finverse: déliaison de %s échouée: %s", row.id, exc)


def _sign_state(user_id: uuid.UUID, platform: str = "web") -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "platform": platform,
            "purpose": "finverse",
            "iat": now,
            "exp": now + _STATE_TTL,
        },
        _STATE_SECRET,
        algorithm="HS256",
    )


def _read_state(state: str) -> dict:
    claims = jwt.decode(state, _STATE_SECRET, algorithms=["HS256"])
    if claims.get("purpose") != "finverse":
        raise jwt.InvalidTokenError("wrong purpose")
    return claims


def _slug(value: str) -> str:
    """An error code from Finverse, safe to put back in a URL."""
    return "".join(c for c in value if c.isalnum() or c in "_-")[:40] or "unknown"


def _back(status: str, platform: str = "web") -> RedirectResponse:
    """Back to the site, or into the app when the flow started there.

    303: the callback may be a POST, and the page it leads to is read with GET.
    """
    if platform == "app":
        url = f"{app_session.APP_RETURN_BASE}banks?finverse={status}"
    else:
        url = f"{settings.frontend_url}/?finverse={status}"
    return RedirectResponse(url=url, status_code=303)
