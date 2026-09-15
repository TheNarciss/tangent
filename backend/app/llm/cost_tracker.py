"""Daily cost tracking + kill-switch for LLM features.

Implements the budget guard described in ADR-015:

- Compute USD cost from token counts (Sonnet 4.6 pricing) + web_search uses
- Atomically increment `llm_daily_cost` via PG UPSERT (race-safe under
  concurrent generations on the same calendar day)
- Block further generation when daily cumulative cost reaches DAILY_CAP_USD

All costs tracked in USD, the currency Anthropic bills in. The cap is set
to $5/day, approximating the EUR 5/day target from ADR-015 without runtime
currency conversion.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import LLMDailyCost

logger = logging.getLogger(__name__)


# -- Pricing (Sonnet 4.6, snapshot June 2026) -------------------------------
# Source: https://www.anthropic.com/pricing
# Update these constants if Anthropic adjusts the published rates.
PRICE_INPUT_PER_MTOK_USD = 3.0
PRICE_OUTPUT_PER_MTOK_USD = 15.0
PRICE_WEB_SEARCH_USD = 0.01  # per individual search invocation


# -- Daily cap --------------------------------------------------------------
# One euro a day, all users together (ADR-015, amended 2026-09-15). Anthropic
# bills in dollars: a dollar stays under a euro whatever the rate does, and
# rounding the cap down is the safe side of a kill-switch. Batches still in
# flight count against it, so three submissions in a day cannot each pass.
DAILY_CAP_USD = 1.0


# -- Timezone anchor --------------------------------------------------------
_PARIS = ZoneInfo("Europe/Paris")


def today_paris() -> date:
    """Today's calendar date in Europe/Paris.

    Used as the partition key on `llm_daily_cost.cost_date`. Anchored to
    server timezone (not the user's) — the cap is global, not per-user.
    """
    return datetime.now(_PARIS).date()


# -- Pure cost computation --------------------------------------------------


def compute_cost_usd(
    input_tokens: int,
    output_tokens: int,
    web_searches_count: int = 0,
) -> float:
    """USD cost of a single LLM call.

    Pure function — no I/O, easy to verify against the published rate card.
    """
    return (
        input_tokens / 1_000_000 * PRICE_INPUT_PER_MTOK_USD
        + output_tokens / 1_000_000 * PRICE_OUTPUT_PER_MTOK_USD
        + web_searches_count * PRICE_WEB_SEARCH_USD
    )


# -- DB-backed budget guard -------------------------------------------------


async def get_today_cost_usd(
    session: AsyncSession,
    today: date | None = None,
) -> float:
    """Cumulative USD spent today across all users. 0.0 if no row yet."""
    if today is None:
        today = today_paris()
    stmt = select(LLMDailyCost.cumulative_cost_usd).where(LLMDailyCost.cost_date == today)
    result = await session.execute(stmt)
    return float(result.scalar() or 0.0)


async def in_flight_estimate_usd(session: AsyncSession) -> float:
    """What the batches still being processed are expected to cost.

    A batch is recorded only when its answers come back, hours later; until
    then its cost is an estimate, and it counts — or three submissions in a
    day would each pass the cap.
    """
    from ..repositories import review_batches as batches_repo

    pending = await batches_repo.list_in_progress(session)
    return float(sum(b.estimated_cost_usd or 0.0 for b in pending))


async def budget_left_usd(session: AsyncSession, today: date | None = None) -> float:
    """What may still be submitted today: the cap, minus spent, minus in flight."""
    spent = await get_today_cost_usd(session, today)
    return DAILY_CAP_USD - spent - await in_flight_estimate_usd(session)


async def is_under_cap(
    session: AsyncSession,
    today: date | None = None,
) -> bool:
    """True iff today's spend, in flight included, is still under DAILY_CAP_USD.

    Call BEFORE starting a new generation. If False, the route layer should
    return HTTP 503 with a "try tomorrow" message (cf ADR-015 §Cost cap).
    """
    return await budget_left_usd(session, today) > 0


async def record_cost(
    session: AsyncSession,
    cost_usd: float,
    today: date | None = None,
) -> float:
    """Atomically add `cost_usd` to today's cumulative cost. Returns new total.

    Race-safe: uses PG `INSERT ... ON CONFLICT (cost_date) DO UPDATE` so two
    concurrent generations cannot stomp each other's increment. The UNIQUE
    constraint on `cost_date` guarantees a single row per day; the UPSERT
    collapses both writers into one consistent row.
    """
    if today is None:
        today = today_paris()

    stmt = pg_insert(LLMDailyCost).values(
        cost_date=today,
        cumulative_cost_usd=cost_usd,
        reviews_count=1,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["cost_date"],
        set_={
            "cumulative_cost_usd": LLMDailyCost.cumulative_cost_usd
            + stmt.excluded.cumulative_cost_usd,
            "reviews_count": LLMDailyCost.reviews_count + stmt.excluded.reviews_count,
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)
    await session.commit()

    new_total = await get_today_cost_usd(session, today)
    logger.info(
        "LLM cost recorded: +$%.4f on %s (cumulative=$%.4f / cap=$%.2f)",
        cost_usd,
        today.isoformat(),
        new_total,
        DAILY_CAP_USD,
    )
    return new_total
