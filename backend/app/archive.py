"""The archive (ADR-034): everything the app knows, written down twice a day.

Morning and evening, for every user, the whole picture as the app sees it
at that moment — profile, accounts, positions, loans, what the method
concludes, the spending picture, the measured performance — and, once per
slot, what the public sources said: the prices of every line anyone holds,
the rates, the list of the year, the market leads. Not to show anything
today: to be able to look back precisely later, and to compute on it.

What is personal is sealed before it reaches the database, with a key
that lives in `.env` and nowhere else (`ARCHIVE_ENCRYPTION_KEY`, Fernet,
the same mechanism as the bank tokens, ADR-012). What came from a public
source is kept in the clear, so SQL can read it. Without the key, nothing
personal is written: the market rows still are, and the log says why.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from cryptography.fernet import Fernet
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect as sa_inspect

from .auth import User
from .data.probe import YAHOO_INDICES
from .db.models import AccountHolding, BankAccount
from .deps import get_user_wealth
from .errors import AppError
from .finance import dashboard, macro, market, market_leads, picks
from .finance import verdicts as verdicts_engine
from .finance.wealth_summary import build_summary
from .repositories import bank_transactions as tx_repo
from .repositories import profile as profile_repo
from .repositories import reviews as reviews_repo
from .repositories import watchlist as watchlist_repo
from .repositories.archive import record_market, record_user
from .routers.profile import _to_out as profile_out
from .routers.spending import build_spending
from .snapshot_job import performance_for

logger = logging.getLogger(__name__)

_PARIS = ZoneInfo("Europe/Paris")
_KEY_ENV = "ARCHIVE_ENCRYPTION_KEY"
SLOTS = ("morning", "evening")


class ArchiveKeyMissing(RuntimeError):
    """No usable archive key: personal data is not written unsealed, ever."""


# ── Sealing ─────────────────────────────────────────────────────────────────


def _fernet() -> Fernet:
    key = os.getenv(_KEY_ENV, "").strip()
    if not key:
        raise ArchiveKeyMissing(f"{_KEY_ENV} manquante : l'archive personnelle n'est pas écrite.")
    try:
        return Fernet(key.encode())
    except ValueError as exc:
        raise ArchiveKeyMissing(f"{_KEY_ENV} invalide : {exc}") from exc


def seal(payload: dict[str, Any]) -> str:
    """The payload as a Fernet token of its JSON. Dates and UUIDs become strings."""
    return _fernet().encrypt(_dumps(payload).encode()).decode()


def unseal(token: str) -> dict[str, Any]:
    """Back from a token to the payload — for the app, never for a route."""
    return dict(json.loads(_fernet().decrypt(token.encode()).decode()))


def _dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str, ensure_ascii=False, separators=(",", ":"))


def _jsonable(payload: dict[str, Any]) -> dict[str, Any]:
    """A copy every JSON writer accepts: dates, UUIDs and floats as plain types."""
    return dict(json.loads(_dumps(payload)))


# ── Payloads ────────────────────────────────────────────────────────────────


def _row(row: Any, *, skip: tuple[str, ...] = ("raw_data",)) -> dict[str, Any]:
    """An ORM row as a dict of its columns, the bulky raw provider payload left out."""
    return {
        attr.key: getattr(row, attr.key)
        for attr in sa_inspect(row).mapper.column_attrs
        if attr.key not in skip
    }


async def user_payload(session: AsyncSession, user: User, *, when: datetime) -> dict[str, Any]:
    """Everything the app knows about one user, right now.

    The computed parts (dashboard, verdicts) are best effort: a source out of
    reach costs that part and leaves a note, never the snapshot.
    """
    wealth = await get_user_wealth(user=user, session=session)
    profile = await profile_repo.get_or_create(session, user.id)
    accounts = (
        (await session.execute(select(BankAccount).where(BankAccount.user_id == user.id)))
        .scalars()
        .all()
    )
    holdings = (
        (await session.execute(select(AccountHolding).where(AccountHolding.user_id == user.id)))
        .scalars()
        .all()
    )
    spending = await build_spending(session, user.id, months=3, today=when.date())
    monthly_spending = await tx_repo.monthly_outflow(session, user.id)
    monthly_saved = await tx_repo.monthly_inflow_to_savings(session, user.id)
    perf = await performance_for(session, user.id)
    watchlist = await watchlist_repo.list_tickers(session, user.id)
    reviews = await reviews_repo.list_reviews(session, user.id, limit=1)

    payload: dict[str, Any] = {
        "taken_at": when,
        "user_id": user.id,
        "profile": profile_out(profile).model_dump(mode="json"),
        "wealth": wealth.model_dump(mode="json"),
        "summary": build_summary(wealth).model_dump(mode="json"),
        "accounts": [_row(a) for a in accounts],
        "holdings": [_row(h) for h in holdings],
        "spending": spending.model_dump(mode="json"),
        "performance": dataclasses.asdict(perf) if perf is not None else None,
        "watchlist": watchlist,
        "latest_review": (
            {
                "review_date": reviews[0].review_date,
                "model_used": reviews[0].model_used,
                "cost_usd": reviews[0].cost_usd,
            }
            if reviews
            else None
        ),
    }
    try:
        verdicts = verdicts_engine.compute_all(
            wealth,
            profile,
            monthly_spending=monthly_spending,
            monthly_saved=monthly_saved,
            perf=perf,
        )
        payload["verdicts"] = [v.model_dump(mode="json") for v in verdicts.verdicts]
    except AppError as exc:
        payload["verdicts"] = None
        payload["verdicts_error"] = str(exc)
    try:
        # yfinance + numpy: off the loop, and a portfolio without positions is not an error here.
        built = await asyncio.to_thread(dashboard.build, wealth=wealth)
        payload["dashboard"] = built.model_dump(mode="json")
    except AppError as exc:
        payload["dashboard"] = None
        payload["dashboard_error"] = str(exc)
    return payload


async def market_payload(session: AsyncSession, *, when: datetime) -> dict[str, Any]:
    """What the public sources say right now, for every line anyone holds."""
    held = list((await session.execute(select(distinct(AccountHolding.ticker)))).scalars().all())
    tickers = sorted({t for t in held if t} | set(YAHOO_INDICES))

    payload: dict[str, Any] = {"taken_at": when, "prices": {}, "macro": {}}
    if tickers:
        try:
            frame = await asyncio.to_thread(
                market.fetch_prices, tickers, period="5d", drop_missing=True
            )
            for ticker in frame.columns:
                series = frame[ticker].dropna()
                if not series.empty:
                    payload["prices"][str(ticker)] = {
                        "date": str(series.index[-1].date()),
                        "close": float(series.iloc[-1]),
                    }
        except AppError as exc:
            payload["prices_error"] = str(exc)
    for name, read in (("policy_rate", macro.risk_free_rate), ("inflation", macro.inflation)):
        try:
            payload["macro"][name] = float(await asyncio.to_thread(read))
        except AppError as exc:
            payload["macro"][f"{name}_error"] = str(exc)
    stored_picks = picks.load()
    payload["picks"] = stored_picks.model_dump(mode="json") if stored_picks else None
    leads = market_leads.load()
    payload["market_leads"] = leads.model_dump(mode="json") if leads else None
    return payload


# ── The run ─────────────────────────────────────────────────────────────────


async def run(
    session: AsyncSession, slot: str, *, when: datetime | None = None
) -> tuple[int, bool]:
    """Archive every user and the market for the slot. Returns (users written, market written).

    One user's failure costs that user's row, never the others'. Without the
    archive key, no personal row is written and the log says so once.
    """
    if slot not in SLOTS:
        raise ValueError(f"slot inconnu : {slot}")
    when = when or datetime.now(UTC)
    day = when.astimezone(_PARIS).date()

    market_ok = False
    try:
        payload = _jsonable(await market_payload(session, when=when))
        await record_market(
            session,
            snapshot_date=day,
            slot=slot,
            taken_at=when,
            payload=payload,
            size_bytes=len(_dumps(payload)),
        )
        await session.commit()
        market_ok = True
    except Exception:
        logger.exception("archive: le marché n'a pas été écrit (%s %s)", day, slot)
        await session.rollback()

    try:
        _fernet()
    except ArchiveKeyMissing as exc:
        logger.error("archive: %s", exc)
        return 0, market_ok

    users = (await session.execute(select(User))).unique().scalars().all()
    written = 0
    for user in users:
        try:
            payload = await user_payload(session, user, when=when)
            await record_user(
                session,
                user.id,
                snapshot_date=day,
                slot=slot,
                taken_at=when,
                sealed=seal(payload),
            )
            await session.commit()
            written += 1
        except Exception:
            logger.exception("archive: utilisateur %s non écrit (%s %s)", user.id, day, slot)
            await session.rollback()
    logger.info(
        "archive %s %s : %d/%d utilisateurs, marché %s", day, slot, written, len(users), market_ok
    )
    return written, market_ok


def slot_for(now: datetime | None = None) -> str:
    """Morning before 14:00 Paris, evening after: what a run started by hand is called."""
    hour = (now or datetime.now(UTC)).astimezone(_PARIS).hour
    return "morning" if hour < 14 else "evening"


__all__ = [
    "SLOTS",
    "ArchiveKeyMissing",
    "market_payload",
    "run",
    "seal",
    "slot_for",
    "unseal",
    "user_payload",
]
