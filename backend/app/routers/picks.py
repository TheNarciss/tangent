"""« La liste de l'année » — today's momentum list and its track record."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from ..auth import User, current_active_user
from ..errors import AppError
from ..finance import momentum

logger = logging.getLogger(__name__)

router = APIRouter(tags=["picks"])


class YearRow(BaseModel):
    year: int
    strategy: float
    universe: float


class TrackRecord(BaseModel):
    since: str  # first month of the backtest
    cagr: float
    universe_cagr: float
    max_drawdown: float
    universe_max_drawdown: float
    turnover: float  # fraction of the list replaced per review
    reviews: int
    guarded_reviews: int
    yearly: list[YearRow]


class PicksResponse(BaseModel):
    as_of: str
    next_review: str
    review: str  # monthly | quarterly | annual
    guard_on: bool
    held: list[str]
    bought: list[str]
    sold: list[str]
    universe_size: int
    indices: list[str]
    top: int
    track_record: TrackRecord


# The universe is ~180 tickers and their whole history: minutes of Yahoo, then
# a month-by-month replay. Once a day is plenty — the list moves once a
# quarter — and every user sees the same list, so one cache serves all.
_CACHE: tuple[datetime, PicksResponse] | None = None
_TTL = timedelta(hours=24)


@router.get("/picks", response_model=PicksResponse)
async def read_picks(user: User = Depends(current_active_user)) -> PicksResponse:
    """The list, what changed since the last review, and the rule's track record.

    Every figure is computed from live sources (index pages, Yahoo). When one
    is out of reach the screen gets a 503 and says so, rather than a stale
    list presented as today's.
    """
    global _CACHE
    if _CACHE and datetime.now(UTC) - _CACHE[0] < _TTL:
        return _CACHE[1]
    try:
        out = await run_in_threadpool(_build)
    except AppError as exc:
        logger.warning("picks: sources injoignables: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    _CACHE = (datetime.now(UTC), out)
    return out


def _build() -> PicksResponse:
    cfg = momentum.config()
    tickers = momentum.universe(cfg)
    daily = momentum.prices(tickers)
    bt = momentum.backtest(daily, cfg)
    picks = momentum.current(daily, cfg)
    return PicksResponse(
        as_of=str(picks.as_of.date()),
        next_review=str(picks.next_review.date()),
        review=cfg.review,
        guard_on=picks.guard_on,
        held=picks.held,
        bought=picks.bought,
        sold=picks.sold,
        universe_size=len(daily.columns),
        indices=cfg.universe,
        top=cfg.top,
        track_record=TrackRecord(
            since=str(bt.strategy.index[0].date()),
            cagr=bt.cagr,
            universe_cagr=bt.universe_cagr,
            max_drawdown=bt.max_drawdown,
            universe_max_drawdown=bt.universe_max_drawdown,
            turnover=bt.turnover,
            reviews=len(bt.reviews),
            guarded_reviews=sum(1 for r in bt.reviews if r.guard_on),
            yearly=[
                YearRow(
                    year=int(year), strategy=float(row["strategy"]), universe=float(row["universe"])
                )
                for year, row in bt.yearly.iterrows()
            ],
        ),
    )
