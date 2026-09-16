"""Enable Banking routes — connect a bank Powens does not cover (ADR-032).

Same shape as the Powens routes: a callback outside /api because the URL is
registered at the provider, everything else under /api/enablebanking.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..aggregator.persist import persist_sync_result
from ..auth import User, current_active_user, current_active_user_optional
from ..auth import session as app_session
from ..db.engine import get_session
from ..db.models import BankAccount, EnableBankingSession
from ..enablebanking import settings
from ..enablebanking.aggregator import is_expired, sync_row
from ..enablebanking.client import EnableBankingClient, EnableBankingError
from ..i18n import Locale, current_locale, t
from ..powens.crypto import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enablebanking", tags=["enablebanking"])
legacy_router = APIRouter(tags=["enablebanking-legacy"])

_STATE_SECRET = os.getenv("OAUTH_STATE_SECRET", "") or os.getenv("JWT_SECRET", "")
_STATE_TTL = timedelta(minutes=15)
CONSENT_DAYS = 180  # the PSD2 ceiling; the bank may allow less
FIRST_SYNC_DAYS = 730  # full history is only readable minutes after consent: take it all
DAILY_SYNC_DAYS = 31


class BankOut(BaseModel):
    name: str
    logo: str | None = None


class AuthorizeIn(BaseModel):
    bank_name: str = Field(min_length=1, max_length=64)
    country: str = Field(default="FR", min_length=2, max_length=2)
    platform: Literal["web", "app"] = "web"  # the app returns to tangent://banks (ADR-035)


class AuthorizeOut(BaseModel):
    url: str


class SessionOut(BaseModel):
    id: uuid.UUID
    bank_name: str
    accounts_count: int
    valid_until: datetime
    expired: bool
    last_sync_at: datetime | None
    last_error: str | None


@router.get("/status")
async def status(user: User = Depends(current_active_user)) -> dict[str, bool]:
    return {"configured": settings.is_configured}


@router.get("/banks", response_model=list[BankOut])
async def banks(
    country: str = "FR",
    user: User = Depends(current_active_user),
    locale: Locale = Depends(current_locale),
) -> list[BankOut]:
    _require_configured(locale)
    try:
        async with EnableBankingClient() as client:
            rows = await client.list_banks(country.upper())
    except EnableBankingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [BankOut(name=str(r["name"]), logo=r.get("logo")) for r in rows if r.get("name")]


@router.post("/authorize", response_model=AuthorizeOut)
async def authorize(
    body: AuthorizeIn,
    user: User = Depends(current_active_user),
    locale: Locale = Depends(current_locale),
) -> AuthorizeOut:
    """Where to send the user so the bank asks for their consent."""
    _require_configured(locale)
    country = body.country.upper()
    try:
        async with EnableBankingClient() as client:
            known = {b["name"]: b for b in await client.list_banks(country) if b.get("name")}
            bank = known.get(body.bank_name)
            if bank is None:
                raise HTTPException(status_code=404, detail="Banque inconnue chez Enable Banking.")
            answer = await client.start_authorization(
                bank_name=body.bank_name,
                country=country,
                psu_type="personal",
                redirect_url=settings.redirect_url,
                state=_sign_state(user.id, body.bank_name, country, body.platform),
                valid_until=_consent_end(bank.get("maximum_consent_validity")),
            )
    except EnableBankingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AuthorizeOut(url=str(answer["url"]))


@legacy_router.get("/auth/enablebanking/callback")
async def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    cookie_user: User | None = Depends(current_active_user_optional),
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """The bank sent the user back: open the session, store it, read everything once.

    From the app the return lands in the system browser, which holds no
    session cookie: the signed state alone says who started the flow.
    """
    try:
        claims = _read_state(state or "")
    except jwt.PyJWTError:
        return _back("error&error=bad_state")
    platform = str(claims.get("platform", "web"))
    if error or not code:
        return _back(f"error&error={error or 'no_code'}", platform)
    user = cookie_user
    if user is not None and claims.get("sub") != str(user.id):
        return _back("error&error=wrong_user", platform)
    if user is None:
        if platform != "app":
            return _back("error&error=wrong_user", platform)
        user = await db.get(User, uuid.UUID(str(claims["sub"])))
        if user is None or not user.is_active:
            return _back("error&error=wrong_user", platform)

    try:
        async with EnableBankingClient() as client:
            opened = await client.create_session(code)
    except EnableBankingError as exc:
        logger.warning("Enable Banking callback user=%s: %s", user.id, exc)
        return _back("error&error=session", platform)

    if not opened.get("accounts"):
        # Restricted mode: the bank answered, but none of its accounts are linked
        # to the application in Enable Banking's control panel.
        return _back("error&error=no_linked_accounts", platform)

    try:
        encrypted = encrypt_token(str(opened["session_id"]))
    except ValueError:
        return _back("error&error=encryption_not_configured", platform)

    aspsp = opened.get("aspsp") or {}
    bank_name = str(aspsp.get("name") or claims.get("bank") or "Banque")
    # One consent per bank and per user: a reconnection replaces the old one,
    # its accounts keep their identity (identification_hash) and their history.
    row = (
        (
            await db.execute(
                select(EnableBankingSession)
                .where(EnableBankingSession.user_id == user.id)
                .where(EnableBankingSession.bank_name == bank_name)
            )
        )
        .scalars()
        .first()
    )
    if row is not None:
        await _revoke(row)
    else:
        row = EnableBankingSession(user_id=user.id, bank_name=bank_name)
        db.add(row)
    row.encrypted_session_id = encrypted
    row.bank_country = str(aspsp.get("country") or claims.get("country") or "FR")[:2]
    row.psu_type = str(opened.get("psu_type") or "personal")
    row.valid_until = _parse_valid_until((opened.get("access") or {}).get("valid_until"))
    row.last_error = None
    await db.commit()
    await db.refresh(row)

    # Full history now, while the bank still allows it. The consent is stored
    # whatever happens next: a failed first read shows on the row, it does
    # not cost the user another trip to the bank.
    try:
        result = await sync_row(db, row, since=date.today() - timedelta(days=FIRST_SYNC_DAYS))
        if result.success:
            await persist_sync_result(db, user.id, result)
    except Exception as exc:
        logger.exception("Enable Banking: première relève en échec pour user=%s", user.id)
        row.last_error = f"{type(exc).__name__}: {exc}"[:500]
    await db.commit()
    return _back("success", platform)


@router.get("/sessions", response_model=list[SessionOut])
async def sessions(
    user: User = Depends(current_active_user), db: AsyncSession = Depends(get_session)
) -> list[SessionOut]:
    rows = (
        (
            await db.execute(
                select(EnableBankingSession)
                .where(EnableBankingSession.user_id == user.id)
                .order_by(EnableBankingSession.created_at)
            )
        )
        .scalars()
        .all()
    )
    out: list[SessionOut] = []
    for row in rows:
        count = await db.scalar(
            select(func.count())
            .select_from(BankAccount)
            .where(BankAccount.user_id == user.id)
            .where(BankAccount.provider == "enablebanking")
            .where(BankAccount.raw_data["enablebanking_session"].astext == str(row.id))
        )
        out.append(
            SessionOut(
                id=row.id,
                bank_name=row.bank_name,
                accounts_count=int(count or 0),
                valid_until=row.valid_until,
                expired=is_expired(row),
                last_sync_at=row.last_sync_at,
                last_error=row.last_error,
            )
        )
    return out


@router.delete("/sessions/{session_row_id}", status_code=204)
async def delete_session(
    session_row_id: uuid.UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    """Revoke at Enable Banking (best effort), then drop the row and its accounts."""
    row = await db.get(EnableBankingSession, session_row_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Connexion inconnue.")
    await _revoke(row)
    accounts = (
        (
            await db.execute(
                select(BankAccount)
                .where(BankAccount.user_id == user.id)
                .where(BankAccount.provider == "enablebanking")
                .where(BankAccount.raw_data["enablebanking_session"].astext == str(row.id))
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


async def _revoke(row: EnableBankingSession) -> None:
    """Best effort: end the consent at Enable Banking; a failure is only logged."""
    try:
        async with EnableBankingClient() as client:
            await client.delete_session(decrypt_token(row.encrypted_session_id))
    except (EnableBankingError, ValueError) as exc:
        logger.warning("Enable Banking: révocation de %s échouée: %s", row.id, exc)


def _require_configured(locale: Locale = "fr") -> None:
    if not settings.is_configured:
        raise HTTPException(
            status_code=503, detail=t(locale, "errors.enablebanking_not_configured")
        )


def _sign_state(user_id: uuid.UUID, bank: str, country: str, platform: str = "web") -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "bank": bank,
            "country": country,
            "platform": platform,
            "purpose": "enablebanking",
            "iat": now,
            "exp": now + _STATE_TTL,
        },
        _STATE_SECRET,
        algorithm="HS256",
    )


def _read_state(state: str) -> dict:
    claims = jwt.decode(state, _STATE_SECRET, algorithms=["HS256"])
    if claims.get("purpose") != "enablebanking":
        raise jwt.InvalidTokenError("wrong purpose")
    return claims


def _consent_end(maximum_seconds: object) -> datetime:
    """180 days, or less when the bank caps its consents lower."""
    days = CONSENT_DAYS
    if isinstance(maximum_seconds, int | float) and maximum_seconds > 0:
        days = min(days, int(maximum_seconds // 86400))
    return datetime.now(UTC) + timedelta(days=max(days, 1))


def _parse_valid_until(value: object) -> datetime:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC) + timedelta(days=CONSENT_DAYS)


def _back(status: str, platform: str = "web") -> RedirectResponse:
    """Back to the site, or into the app when the flow started there."""
    if platform == "app":
        return RedirectResponse(url=f"{app_session.APP_RETURN_BASE}banks?enablebanking={status}")
    return RedirectResponse(url=f"{settings.frontend_url}/?enablebanking={status}")
