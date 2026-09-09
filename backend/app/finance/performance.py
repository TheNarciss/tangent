"""Real performance of a real account: TWR, TRI, drawdown.

Two questions, two numbers, and the gap between them is worth knowing
(étude §7.7):

- **TWR** answers « how did the strategy do », independently of when money
  was paid in. It chains the return of each sub-period between two flows.
  It is what a fund factsheet reports and what GIPS requires.
- **TRI** (money-weighted) answers « what did *my* money earn, with *my*
  timing ». It is the rate that discounts every contribution and the final
  value back to zero.

Both read the snapshot series (`portfolio_snapshots`), the app's only real
history: the "as if held today" curve applies today's weights to the past
and is a backtest of the current allocation, legitimate for sizing risk,
illegitimate as the account's history.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from itertools import pairwise

from ..models import Wealth

logger = logging.getLogger(__name__)

# Below this the sub-period return is not meaningful (a pocket worth nothing).
_MIN_VALUE = 1.0
DAYS_PER_YEAR = 365.0
# Annualizing a short window turns a good month into an absurd yearly rate:
# below six months only the cumulative return is reported.
MIN_DAYS_TO_ANNUALIZE = 180


# The PEA's uninvested cash is part of the pocket and moves only when money
# enters or leaves it, so it rides along as a line priced at one euro.
CASH_KEY = "__cash__"


def snapshot_inputs(wealth: Wealth) -> tuple[float, dict[str, float], dict[str, float]]:
    """(total value, quantities, prices) of the pocket a snapshot can measure.

    Only the lines whose quantity is known: listed positions plus the PEA's
    cash. A wrapper the provider values in bulk (a life insurance with no
    line detail) is left out — with no quantity, a contribution into it
    cannot be told from a gain, and counting it would flatter the return.
    """
    quantities: dict[str, float] = {}
    prices: dict[str, float] = {}
    total = 0.0
    for account in wealth.investment_accounts:
        for position in account.positions:
            if position.quantity <= 0:
                continue
            quantities[position.ticker] = quantities.get(position.ticker, 0.0) + position.quantity
            prices[position.ticker] = position.current_value / position.quantity
            total += position.current_value
    cash = wealth.pea_cash_total
    if cash:
        quantities[CASH_KEY] = cash
        prices[CASH_KEY] = 1.0
        total += cash
    return total, quantities, prices


@dataclass(frozen=True)
class Point:
    """One day of the series: value, and the money paid in since the day before."""

    day: date
    value: float
    net_flow: float


@dataclass(frozen=True)
class Performance:
    """What the snapshot series says about the account."""

    start: date
    end: date
    days: int
    twr: float | None
    """Time-weighted return over the whole window, cumulative."""
    twr_annualized: float | None
    irr: float | None
    """Money-weighted (annualized), the saver's own result."""
    behaviour_gap: float | None
    """TRI − TWR annualized: what the timing of the contributions cost or won."""
    index: list[float]
    """TWR index, base 1 at the first point."""
    drawdown: float
    """Current fall from the index's high, ≤ 0."""
    max_drawdown: float
    peak_day: date | None
    net_flows: float
    first_value: float
    last_value: float


def sub_period_return(previous_value: float, value: float, net_flow: float) -> float | None:
    """Return of one sub-period, with the contribution taken out of the numerator.

    (V_t − F_t) / V_(t−1) − 1: the money paid in during the period is not
    performance. None when the previous value is too small to divide by.
    """
    if previous_value < _MIN_VALUE:
        return None
    return (value - net_flow) / previous_value - 1.0


def money_weighted_return(points: list[Point]) -> float | None:
    """Annualized internal rate of return over the series (XIRR).

    Cash flows, from the saver's point of view: the opening value and every
    contribution go out, the closing value comes back. Solved by bisection —
    slower than Newton and immune to the flat spots that make Newton diverge
    on a short series.
    """
    if len(points) < 2:
        return None
    start, end = points[0].day, points[-1].day
    span = (end - start).days
    if span <= 0:
        return None

    flows: list[tuple[int, float]] = [(0, -points[0].value)]
    for p in points[1:]:
        if p.net_flow:
            flows.append(((p.day - start).days, -p.net_flow))
    flows.append((span, points[-1].value))
    if all(amount <= 0 for _, amount in flows) or all(amount >= 0 for _, amount in flows):
        return None

    def npv(rate: float) -> float:
        return sum(amount / (1.0 + rate) ** (days / DAYS_PER_YEAR) for days, amount in flows)

    low, high = -0.9999, 10.0
    if npv(low) * npv(high) > 0:
        return None
    for _ in range(200):
        mid = (low + high) / 2
        if npv(low) * npv(mid) <= 0:
            high = mid
        else:
            low = mid
    return (low + high) / 2


def compute(points: list[Point]) -> Performance | None:
    """Chain the sub-periods into a TWR index, then read everything off it."""
    usable = [p for p in points if p.value >= 0]
    if len(usable) < 2:
        return None

    index = [1.0]
    for previous, current in pairwise(usable):
        r = sub_period_return(previous.value, current.value, current.net_flow)
        index.append(index[-1] * (1.0 + r) if r is not None else index[-1])

    peak = index[0]
    peak_at = 0
    max_dd = 0.0
    running_peak = index[0]
    for i, value in enumerate(index):
        if value > running_peak:
            running_peak = value
        max_dd = min(max_dd, value / running_peak - 1.0)
        if value >= peak:
            peak, peak_at = value, i
    drawdown = index[-1] / peak - 1.0 if peak > 0 else 0.0

    start, end = usable[0].day, usable[-1].day
    days = (end - start).days
    twr = index[-1] - 1.0
    years = days / DAYS_PER_YEAR
    long_enough = days >= MIN_DAYS_TO_ANNUALIZE
    twr_annualized = (
        index[-1] ** (1 / years) - 1.0 if long_enough and years > 0 and index[-1] > 0 else None
    )
    irr = money_weighted_return(usable) if long_enough else None
    gap = irr - twr_annualized if irr is not None and twr_annualized is not None else None

    return Performance(
        start=start,
        end=end,
        days=days,
        twr=twr,
        twr_annualized=twr_annualized,
        irr=irr,
        behaviour_gap=gap,
        index=index,
        drawdown=drawdown,
        max_drawdown=max_dd,
        peak_day=usable[peak_at].day,
        net_flows=sum(p.net_flow for p in usable[1:]),
        first_value=usable[0].value,
        last_value=usable[-1].value,
    )
