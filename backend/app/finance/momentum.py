"""« La liste de l'année » — cross-sectional momentum on European large caps.

The only form of « buy these, sell those » with a century of evidence behind
it: the stocks that rose the most over the past twelve months, skipping the
latest, keep rising for a while (Jegadeesh & Titman 1993; Rouwenhorst 1998
finds it stronger in Europe). It is a rule, not a forecast: the list falls
out of a computation anyone can redo.

What this module does not pretend: the premium is an expectation, not a
guarantee. Momentum crashed −45 % in two months at the 2009 rebound (Daniel &
Moskowitz 2016), which is why the list empties after a down year and why the
screen caps the sleeve at a fraction of one's equities.

Everything is read live — the universe from the daily holdings of an index
fund, each ISIN's quote from OpenFIGI, the prices from Yahoo — and
`config/momentum.yaml` holds nothing but the rule.

Run `python -m app.finance.momentum` on a machine that reaches Yahoo for the
backtest and today's list.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml
from pydantic import BaseModel, Field

from ..data import xtrackers
from ..errors import ConfigurationError, DataSourceError
from . import classification, market

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "momentum.yaml"

_REVIEW_MONTHS = {"monthly": 1, "quarterly": 3, "annual": 12}


class Guard(BaseModel):
    market_lookback_months: int = Field(12, ge=1)


class MomentumConfig(BaseModel):
    universe: list[str]
    lookback_months: int = Field(12, ge=2)
    skip_months: int = Field(1, ge=0)
    top: int = Field(30, ge=1)
    min_history_months: int = Field(12, ge=1)
    review: str = "quarterly"
    cost_per_trade: float = Field(0.002, ge=0)
    guard: Guard = Field(default_factory=Guard)

    @property
    def review_months(self) -> int:
        try:
            return _REVIEW_MONTHS[self.review]
        except KeyError as exc:
            raise ConfigurationError(f"momentum.yaml: review inconnu « {self.review} »") from exc


@lru_cache(maxsize=1)
def config() -> MomentumConfig:
    if not _PATH.exists():
        raise ConfigurationError("momentum.yaml introuvable.")
    try:
        return MomentumConfig.model_validate(yaml.safe_load(_PATH.read_text()) or {})
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError(f"momentum.yaml malformé: {exc}") from exc


# ── Data ───────────────────────────────────────────────────────────────────


def universe(cfg: MomentumConfig | None = None) -> list[str]:
    """Every euro-quoted constituent of every fund in the rule, once, as Yahoo names it.

    The fund's file gives ISINs; OpenFIGI gives each one its home venue. Lines
    quoted in another currency, and lines with no venue we can read (a rights
    issue, a forward), are left out — a euro investor's momentum has no
    exchange rate inside it.
    """
    c = cfg or config()
    isins: list[str] = []
    venues: dict[str, str] = {}
    for fund in c.universe:
        for line in xtrackers.constituents(fund):
            if line.currency == "EUR" and line.isin not in isins:
                isins.append(line.isin)
                if line.venue:
                    venues[line.isin] = line.venue
    quoted = classification.quotes(isins, prefer=venues)
    tickers: list[str] = []
    for isin in isins:
        quote = quoted.get(isin)
        if quote and quote.currency == "EUR" and quote.ticker not in tickers:
            tickers.append(quote.ticker)
    if not tickers:
        raise DataSourceError("Aucun titre de l'univers n'a de cotation lisible.")
    logger.info("univers momentum : %d ISIN en euros, %d cotations", len(isins), len(tickers))
    return tickers


def month_ends(prices: pd.DataFrame) -> pd.DataFrame:
    """Last available close of each month; the grid every score is built on."""
    return prices.resample("ME").last()


def prices(tickers: list[str]) -> pd.DataFrame:
    """Daily adjusted closes for the whole universe, unknown tickers left out."""
    return market.fetch_prices(tickers, period="max", drop_missing=True)


# ── The rule ───────────────────────────────────────────────────────────────


def scores(monthly: pd.DataFrame, at: int, cfg: MomentumConfig) -> pd.Series:
    """Momentum score of every eligible ticker at row `at` of the monthly grid.

    Return from `lookback` months ago to `skip` months ago, divided by the
    volatility of monthly returns over the same window. Tickers with a gap in
    their history over the window, or too young, are left out.
    """
    start = at - cfg.lookback_months
    end = at - cfg.skip_months
    if start < 0 or end <= start:
        return pd.Series(dtype=float)
    window = monthly.iloc[start : end + 1]
    complete = window.dropna(axis=1, how="any")
    if complete.empty:
        return pd.Series(dtype=float)
    history = monthly.iloc[max(0, at - cfg.min_history_months) : at + 1]
    old_enough = history.notna().sum() >= cfg.min_history_months
    complete = complete.loc[:, old_enough.reindex(complete.columns, fill_value=False)]
    ret = complete.iloc[-1] / complete.iloc[0] - 1.0
    vol = complete.pct_change().dropna().std().replace(0.0, math.nan)
    return (ret / vol).dropna().sort_values(ascending=False)


def market_is_falling(monthly: pd.DataFrame, at: int, cfg: MomentumConfig) -> bool:
    """The guard: the equal-weight universe lost money over the past year."""
    back = at - cfg.guard.market_lookback_months
    if back < 0:
        return False
    window = monthly.iloc[[back, at]].dropna(axis=1, how="any")
    if window.empty:
        return False
    return bool((window.iloc[1] / window.iloc[0] - 1.0).mean() < 0)


def select(monthly: pd.DataFrame, at: int, cfg: MomentumConfig) -> list[str]:
    """The list at row `at`: empty when the guard is on."""
    if market_is_falling(monthly, at, cfg):
        return []
    return list(scores(monthly, at, cfg).head(cfg.top).index)


# ── The backtest ───────────────────────────────────────────────────────────


@dataclass
class Review:
    date: pd.Timestamp
    held: list[str]
    bought: list[str]
    sold: list[str]
    guard_on: bool


@dataclass
class Backtest:
    reviews: list[Review]
    strategy: pd.Series  # growth of 1 €, monthly, costs deducted
    universe: pd.Series  # growth of 1 € in the equal-weight universe
    turnover: float  # average fraction of the list replaced per review
    yearly: pd.DataFrame = field(default_factory=pd.DataFrame)  # year × (strategy, universe)

    @property
    def cagr(self) -> float:
        return _cagr(self.strategy)

    @property
    def universe_cagr(self) -> float:
        return _cagr(self.universe)

    @property
    def max_drawdown(self) -> float:
        return float((self.strategy / self.strategy.cummax() - 1.0).min())

    @property
    def universe_max_drawdown(self) -> float:
        return float((self.universe / self.universe.cummax() - 1.0).min())


def _cagr(growth: pd.Series) -> float:
    years = len(growth) / 12
    return float(growth.iloc[-1] ** (1 / years) - 1.0) if years > 0 else 0.0


def backtest(daily: pd.DataFrame, cfg: MomentumConfig | None = None) -> Backtest:
    """Replay the rule month by month on the price history, costs included.

    The list is refreshed every `review_months`; between two reviews the
    holdings drift with their prices (no monthly rebalancing, which would
    cost more than it earns at equal weights). Each review pays
    `cost_per_trade` on every name bought and every name sold.
    """
    c = cfg or config()
    monthly = month_ends(daily)
    rets = monthly.pct_change()
    strategy = [1.0]
    universe_growth = [1.0]
    reviews: list[Review] = []
    held: list[str] = []
    weights = pd.Series(dtype=float)
    turnovers: list[float] = []

    # The first review happens at `first`; returns accrue from the month after,
    # for the strategy and for the universe alike, so the two start together.
    first = c.lookback_months + 1
    for at in range(first, len(monthly)):
        if at > first:
            # the month's return on what was held, at drifting weights
            month = rets.iloc[at]
            if len(weights):
                valid = weights.index.intersection(month.dropna().index)
                gain = float(
                    (weights[valid] * (1.0 + month[valid])).sum()
                    + (weights.sum() - weights[valid].sum())
                )
                weights = weights[valid] * (1.0 + month[valid])
                weights = weights / gain if gain > 0 else weights
            else:
                gain = 1.0
            strategy.append(strategy[-1] * gain)
            universe_growth.append(universe_growth[-1] * (1.0 + float(month.dropna().mean())))

        if (at - first) % c.review_months == 0:
            new = select(monthly, at, c)
            bought = [t for t in new if t not in held]
            sold = [t for t in held if t not in new]
            if held or new:
                turnovers.append(len(sold) / len(held) if held else 1.0)
            cost = c.cost_per_trade * (len(bought) + len(sold)) / max(len(new), len(held), 1)
            strategy[-1] *= 1.0 - cost
            reviews.append(Review(monthly.index[at], new, bought, sold, guard_on=not new))
            held = new
            weights = pd.Series(1.0 / len(new), index=new) if new else pd.Series(dtype=float)

    index = monthly.index[first:]
    s = pd.Series(strategy, index=index)
    u = pd.Series(universe_growth, index=index)
    yearly = pd.DataFrame(
        {
            "strategy": s.resample("YE").last().pct_change(),
            "universe": u.resample("YE").last().pct_change(),
        }
    ).dropna()
    yearly.index = yearly.index.year
    return Backtest(
        reviews, s, u, float(sum(turnovers) / len(turnovers)) if turnovers else 0.0, yearly
    )


# ── Today's list ───────────────────────────────────────────────────────────


@dataclass
class Picks:
    as_of: pd.Timestamp
    held: list[str]
    bought: list[str]
    sold: list[str]
    guard_on: bool
    next_review: pd.Timestamp


def current(daily: pd.DataFrame, cfg: MomentumConfig | None = None) -> Picks:
    """Today's list, and what changed since the previous review."""
    c = cfg or config()
    monthly = month_ends(daily)
    at = len(monthly) - 1
    now = select(monthly, at, c)
    before = (
        select(monthly, at - c.review_months, c)
        if at - c.review_months >= c.lookback_months
        else []
    )
    next_review = (monthly.index[at] + pd.DateOffset(months=c.review_months)).normalize()
    return Picks(
        as_of=monthly.index[at],
        held=now,
        bought=[t for t in now if t not in before],
        sold=[t for t in before if t not in now],
        guard_on=not now and market_is_falling(monthly, at, c),
        next_review=next_review,
    )


# ── CLI ────────────────────────────────────────────────────────────────────


def _report() -> str:
    c = config()
    tickers = universe(c)
    daily = prices(tickers)
    bt = backtest(daily, c)
    picks = current(daily, c)
    lines = [
        f"Univers : {len(tickers)} titres ({', '.join(c.universe)}), cours depuis {daily.index[0].date()}",
        "Attention : constituants actuels — les sortants d'hier manquent, le résultat est flatté.",
        "",
        f"{'':<12}{'stratégie':>12}{'univers':>12}",
        f"{'CAGR':<12}{bt.cagr:>12.1%}{bt.universe_cagr:>12.1%}",
        f"{'pire chute':<12}{bt.max_drawdown:>12.1%}{bt.universe_max_drawdown:>12.1%}",
        f"{'rotation':<12}{bt.turnover:>12.0%}{'':>12}   par revue ({c.review})",
        "",
        "Par année :",
    ]
    for year, row in bt.yearly.iterrows():
        lines.append(f"  {year}  {row['strategy']:>+7.1%}   univers {row['universe']:>+7.1%}")
    guarded = sum(1 for r in bt.reviews if r.guard_on)
    lines += ["", f"Frein actif sur {guarded} revues sur {len(bt.reviews)}.", ""]
    if picks.guard_on:
        lines.append(
            f"Liste au {picks.as_of.date()} : VIDE — le marché a perdu sur un an, poche en cash."
        )
    else:
        lines.append(
            f"Liste au {picks.as_of.date()} ({len(picks.held)} titres) : {', '.join(picks.held)}"
        )
        lines.append(f"  achète : {', '.join(picks.bought) or '—'}")
        lines.append(f"  vends  : {', '.join(picks.sold) or '—'}")
    lines.append(f"Prochaine revue : {picks.next_review.date()}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(_report())
