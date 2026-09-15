"""Export — everything Tangent knows and computes about one account, in one JSON.

For debugging: the file replays every screen (patrimoine, dashboard, verdicts,
projection, briefings) plus the method's intermediate steps (how each line
was classified, which dates and series each crisis was measured on), and
the whole archive (ADR-034): what the app knew morning and evening, every
day, opened with the archive key since the data is the person's own. Each
section is computed on its own, so one failing screen appears as an error
entry instead of blanking the export — a debugging file must never be empty
because of the bug it was meant to show.

Never included: the password hash, session tokens, bank credentials.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from .. import archive
from ..auth import User, current_active_user
from ..deps import get_session, get_user_wealth
from ..finance import (
    classification,
    dashboard,
    projection,
    stress,
    timeseries,
    verdicts,
    withdrawal,
)
from ..finance.wealth_summary import build_summary as build_wealth_summary
from ..models import Wealth
from ..repositories import account_holdings as holdings_repo
from ..repositories import bank_accounts as accounts_repo
from ..repositories import bank_transactions as tx_repo
from ..repositories import profile as profile_repo
from ..repositories import reviews as reviews_repo
from ..snapshot_job import performance_for
from . import accounts as accounts_router
from . import profile as profile_router
from . import reviews as reviews_router

logger = logging.getLogger(__name__)

router = APIRouter(tags=["export"])


@router.get("/export")
async def export_everything(
    wealth: Wealth = Depends(get_user_wealth),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """The whole account, data and computed results, as one JSON document."""
    profile = await profile_repo.get_or_create(session, user.id)
    out: dict[str, Any] = {
        "meta": {
            "exported_at": datetime.now(UTC).isoformat(),
            "user_id": str(user.id),
            "email": user.email,
        },
        "profile": profile_router._to_out(profile),
        "wealth": wealth,
    }

    async def accounts() -> Any:
        return await accounts_router.list_accounts(user, session)

    async def holdings() -> Any:
        rows = await accounts_repo.list_accounts(session, user.id)
        return {
            str(row.id): await holdings_repo.list_holdings(session, user.id, row.id) for row in rows
        }

    async def transactions() -> Any:
        return await accounts_router.list_recent_transactions(100, user, session)

    async def reviews() -> Any:
        rows = await reviews_repo.list_reviews(session, user.id, limit=30)
        return [reviews_router._to_response(r) for r in rows]

    async def verdicts_section() -> Any:
        return verdicts.compute_all(
            wealth,
            profile,
            monthly_spending=await tx_repo.monthly_outflow(session, user.id),
            monthly_saved=await tx_repo.monthly_inflow_to_savings(session, user.id),
            perf=await performance_for(session, user.id),
        )

    async def projection_section() -> Any:
        return await run_in_threadpool(
            projection.build,
            profile.monthly_dca or 0.0,
            profile.horizon_years or 10,
            profile.goal_amount,
            profile.default_broker,
            wealth=wealth,
            weighted_ter=await holdings_repo.get_weighted_ter(session, user.id),
        )

    sections: dict[str, Callable[[], Awaitable[Any]]] = {
        "wealth_summary": lambda: run_in_threadpool(build_wealth_summary, wealth),
        "accounts": accounts,
        "holdings": holdings,
        "recent_transactions": transactions,
        "dashboard": lambda: run_in_threadpool(dashboard.build, wealth=wealth),
        "timeseries": lambda: run_in_threadpool(timeseries.build, wealth=wealth),
        "verdicts": verdicts_section,
        "projection": projection_section,
        "withdrawal_rate": lambda: run_in_threadpool(withdrawal.default_withdrawal_rate),
        "reviews": reviews,
        "method": lambda: run_in_threadpool(_method, wealth),
        "archive": lambda: archive.user_history(session, user.id),
    }
    for name, build in sections.items():
        try:
            out[name] = await build()
        except Exception as exc:
            logger.warning("export: section %s en erreur: %s", name, exc)
            out[name] = {"error": f"{type(exc).__name__}: {exc}"}
    return jsonable_encoder(out)


def _method(wealth: Wealth) -> dict[str, Any]:
    """The method's intermediate steps: what the screens do not show."""
    positions = [p for a in wealth.investment_accounts for p in a.positions]
    known = classification.classify_many([(p.label, p.isin) for p in positions])
    cfg = stress.config()
    held = stress.pockets(wealth, cfg)
    episodes = []
    for s in cfg.scenarios:
        measured = stress.measured_returns(s, cfg)
        episodes.append(
            {
                "id": s.id,
                "search_span": [s.window.since, s.window.until] if s.window else None,
                "window": stress.window_of(s, cfg),
                "measured": measured,
                "declared": s.returns,
                "pockets": [
                    {
                        "asset_class": p.asset_class,
                        "ticker": p.quote.ticker if p.quote else None,
                        "amount": p.amount,
                        "return": ret,
                        "level": level,
                    }
                    for p in held
                    for ret, level in [stress.pocket_return_and_level(p, s, measured)]
                ],
            }
        )
    return {
        "classification": [
            {"label": p.label, "isin": p.isin, "ticker": p.ticker, **vars(k)}
            for p, k in zip(positions, known, strict=True)
        ],
        "pockets": held,
        "episodes": episodes,
    }
