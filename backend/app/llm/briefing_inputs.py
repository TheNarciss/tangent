"""Everything the app knows about a user, gathered once for the briefing.

The two ways a briefing is made (the night's batch, the admin's on-demand
stream) read the same things: the method's verdicts, the spending picture,
the money put aside each month, the measured performance, the daily
readings of the portfolio, the watchlist, and yesterday's briefing so
today's can say what changed. What is the same for everyone — the
market leads, the list of the year, the observed rates — is read once.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Profile
from ..errors import AppError
from ..finance import macro, market_leads, performance, picks
from ..finance import verdicts as verdicts_engine
from ..finance.performance import Performance, Point
from ..models import MarketLead, PicksResponse, Verdict, Wealth
from ..repositories import bank_transactions as tx_repo
from ..repositories import reviews as reviews_repo
from ..repositories import snapshots as snapshots_repo
from ..repositories import watchlist as watchlist_repo
from ..routers.spending import SpendingResponse, build_spending

HISTORY_DAYS = 31
"""Daily readings handed to the briefing: a month, enough for « depuis hier » and « ce mois-ci »."""


@dataclass(frozen=True)
class SharedInputs:
    """What every briefing of the night receives alike."""

    market_leads: list[MarketLead] = field(default_factory=list)
    picks: PicksResponse | None = None
    macro: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class UserInputs:
    """What one user's briefing receives on top of the wealth and the profile."""

    verdicts: list[Verdict]
    spending: SpendingResponse | None
    monthly_saved: float | None
    performance: Performance | None
    history: list[Point]
    watchlist: list[str]
    previous_review: str | None


def collect_shared() -> SharedInputs:
    """The leads, the list and the rates — read once, best effort each."""
    collected = market_leads.load()
    rates: dict[str, float] = {}
    for name, read in (("policy_rate", macro.risk_free_rate), ("inflation", macro.inflation)):
        try:
            rates[name] = float(read())
        except AppError:
            continue
    return SharedInputs(
        market_leads=collected.leads if collected else [],
        picks=picks.load(),
        macro=rates,
    )


async def collect_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    wealth: Wealth,
    profile: Profile,
    *,
    today: date | None = None,
) -> UserInputs:
    """Everything the app knows about the user beyond the wealth itself.

    The spending picture is best effort: a failure there costs the section,
    never the briefing. The verdicts are not: they are the method's word.
    """
    today = today or date.today()
    monthly_spending = await tx_repo.monthly_outflow(session, user_id)
    monthly_saved = await tx_repo.monthly_inflow_to_savings(session, user_id)
    rows = await snapshots_repo.list_snapshots(session, user_id)
    points = [Point(day=r.snapshot_date, value=r.total_value, net_flow=r.net_flow) for r in rows]
    perf = performance.compute(points)
    since = today - timedelta(days=HISTORY_DAYS)
    history = [p for p in points if p.day >= since]
    verdicts = verdicts_engine.compute_all(
        wealth, profile, monthly_spending=monthly_spending, monthly_saved=monthly_saved, perf=perf
    ).verdicts
    try:
        spending: SpendingResponse | None = await build_spending(
            session, user_id, months=3, today=today
        )
    except Exception:
        spending = None
    watchlist = await watchlist_repo.list_tickers(session, user_id)
    previous = await reviews_repo.list_reviews(session, user_id, to_date=today, limit=1)
    previous_review = previous[0].content if previous and previous[0].content else None
    return UserInputs(
        verdicts=verdicts,
        spending=spending,
        monthly_saved=monthly_saved,
        performance=perf,
        history=history,
        watchlist=watchlist,
        previous_review=previous_review,
    )


async def collect_shared_async() -> SharedInputs:
    """`collect_shared` off the event loop: the rates may go to the network once."""
    return await asyncio.to_thread(collect_shared)


__all__ = [
    "HISTORY_DAYS",
    "SharedInputs",
    "UserInputs",
    "collect_shared",
    "collect_shared_async",
    "collect_user",
]
