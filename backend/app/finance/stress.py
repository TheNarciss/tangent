"""Stress tests — what the past crises would have done to this patrimony.

Replayed on **asset classes**, not on the user's own price history: no
French ETF has data before 2009, so replaying 2000 or 2008 on real prices is
impossible — which is why this screen used to hold three windows, all after
2020, and left out the deepest fall of the last forty years. Mapping each
line to a class and replaying the class is what a manager does («  rejeu
historique », EBA 2018 vocabulary), and it works from the first day.

Every figure is peak-to-trough on daily data **for a euro investor**, so the
currency move is already inside it. The dates of each crisis come from the
world-equity series itself; every class — and every line whose own history
reaches back that far — is then measured between the same two days
(`episodes`). The figures written in `config/stress_scenarios.yaml` are the
fallbacks, aligned on what the loop measures. The same episode seen from a
dollar investor sits next to the euro one, and the gap is what the dollar cost
or paid — in 2008 it cushioned five points, in 2000-03 it deepened the fall.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ..errors import ConfigurationError
from ..models import StressTestResult, Wealth
from . import classification, episodes

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "stress_scenarios.yaml"

# Livrets are capital-guaranteed and the euro fund never marks to market:
# a class we cannot place is treated as cash rather than as a market asset.
FALLBACK_CLASS = "cash"


class Window(BaseModel):
    """The episode's dates, machine-readable, next to the human ones."""

    since: str = Field(alias="from")
    until: str = Field(alias="to")

    model_config = {"populate_by_name": True}


class IndexSeries(BaseModel):
    """Where to find a daily index for one asset class."""

    provider: str
    id: str
    currency: str = "USD"
    in_euros: bool = True  # False keeps the local-currency move, for the currency effect


class Scenario(BaseModel):
    id: str
    label: str
    window: Window | None = None
    start: str
    end: str
    description: str
    returns: dict[str, float]

    def ret(
        self,
        asset_class: str,
        measured: dict[str, float] | None = None,
        borrows_from: dict[str, str] | None = None,
    ) -> float:
        """What the class did: measured on its own index when we could, declared otherwise.

        A class with no declared figure borrows one, rather than defaulting to
        zero: a pocket reported as untouched by a crash is a worse answer than
        a pocket reported with its neighbour's amplitude.
        """
        if measured and asset_class in measured:
            return measured[asset_class]
        if asset_class in self.returns:
            return self.returns[asset_class]
        lends = (borrows_from or {}).get(asset_class)
        if lends is not None:
            return self.returns.get(lends, 0.0)
        return 0.0

    def currency_effect(self, measured: dict[str, float] | None = None) -> float | None:
        """Points the euro/dollar move added to (or took from) world equities.

        Both legs come from the same source — measured together, or declared
        together. None when the episode has no comparable dollar figure.
        """
        m = measured or {}
        if "equity_world" in m and "equity_world_usd" in m:
            return m["equity_world"] - m["equity_world_usd"]
        if "equity_world_usd" not in self.returns:
            return None
        return self.returns["equity_world"] - self.returns["equity_world_usd"]


class ScenariosConfig(BaseModel):
    class_series: dict[str, list[IndexSeries]] = Field(default_factory=dict)
    fallback_class: dict[str, str] = Field(default_factory=dict)
    reference_class: str = "equity_world"  # whose series dates the crises
    class_map: dict[str, str]
    default_asset_class: str
    envelope_classes: dict[str, str]
    account_classes: dict[str, str]
    scenarios: list[Scenario] = Field(min_length=1)


def _load() -> ScenariosConfig:
    if not _PATH.exists():
        raise ConfigurationError(f"Fichier de scénarios de stress manquant: {_PATH}.")
    try:
        raw = yaml.safe_load(_PATH.read_text())
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"YAML invalide dans {_PATH.name}: {exc}") from exc
    try:
        return ScenariosConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigurationError(f"Schéma {_PATH.name} invalide: {exc}") from exc


_CONFIG: ScenariosConfig | None = None


def config() -> ScenariosConfig:
    """Lazy-load the scenario library; cached for the process lifetime."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = _load()
    return _CONFIG


@dataclass(frozen=True)
class Pocket:
    """One slice of the patrimony, and the finest history we could reach for it.

    `quote` is the line's own Yahoo symbol when OpenFIGI named a venue we can
    read. A pocket that has one is measured on its actual price; the rest fall
    back to their asset class.
    """

    asset_class: str
    amount: float
    quote: classification.Quote | None = None


def pockets(wealth: Wealth, cfg: ScenariosConfig | None = None) -> list[Pocket]:
    """Every euro of the patrimony, split into what a scenario can price.

    A listed line takes the class of what it actually is (ADR-025), a wrapper
    valued in bulk the class of its type, an envelope the class of its type.
    Everything is counted, so the euro amount a scenario produces is about the
    patrimony the user actually has, not about one pocket of it.
    """
    c = cfg or config()
    out: list[Pocket] = []

    def add(asset_class: str, amount: float, quote: classification.Quote | None = None) -> None:
        if amount:
            out.append(Pocket(asset_class, amount, quote))

    # Classified in one batch: a Pydantic position is not hashable, so the
    # answers are consumed in the same order the questions were asked.
    positions = [p for a in wealth.investment_accounts for p in a.positions]
    what = iter(classification.classify_many([(p.label, p.isin) for p in positions]))

    for account in wealth.investment_accounts:
        if account.positions:
            for position in account.positions:
                known = next(what)
                add(
                    c.class_map.get(known.asset_class, c.default_asset_class),
                    position.current_value,
                    known.quote,
                )
        else:
            add(c.account_classes.get(account.account_type, c.default_asset_class), account.balance)
    for cash in wealth.pea_cash_accounts:
        add(FALLBACK_CLASS, cash.balance)
    for envelope in wealth.envelopes:
        add(c.envelope_classes.get(envelope.envelope_type, FALLBACK_CLASS), envelope.balance)
    return out


def exposure(wealth: Wealth, cfg: ScenariosConfig | None = None) -> dict[str, float]:
    """€ held in each asset class, across the whole patrimony."""
    return _by_class(pockets(wealth, cfg))


def _by_class(held: list[Pocket]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for pocket in held:
        totals[pocket.asset_class] = totals.get(pocket.asset_class, 0.0) + pocket.amount
    return totals


def measured_returns(scenario: Scenario, cfg: ScenariosConfig | None = None) -> dict[str, float]:
    """Classes whose fall we could measure on their own index, for this episode.

    The loop that replaces hand-copied figures: every class declaring a series
    is tried, and the ones the series does not cover simply stay out. Adding a
    class to `class_series` is enough — there is nothing to recompute by hand.
    """
    c = cfg or config()
    if scenario.window is None:
        return {}

    window = window_of(scenario, c)
    out: dict[str, float] = {}
    for asset_class, candidates in c.class_series.items():
        for series in candidates:
            fall = episodes.measure(
                series.id, series.provider, series.currency, window, in_euros=series.in_euros
            )
            if fall is not None:
                out[asset_class] = fall
                break
    return out


# The dates of each crisis, derived once per process from the reference series.
_WINDOWS: dict[str, tuple[str, str]] = {}


def window_of(scenario: Scenario, cfg: ScenariosConfig | None = None) -> tuple[str, str]:
    """The two days every class is measured between.

    The declared window is a search span; the crisis's own peak and trough
    inside it come from the reference series (world equities in euros). When
    that series is out of reach the span itself is used, as before.
    """
    c = cfg or config()
    if scenario.window is None:
        raise ConfigurationError(f"Scénario {scenario.id} sans fenêtre.")
    span = (scenario.window.since, scenario.window.until)
    if scenario.id in _WINDOWS:
        return _WINDOWS[scenario.id]
    for series in c.class_series.get(c.reference_class, []):
        dated = episodes.peak_to_trough(series.id, series.provider, series.currency, span)
        if dated is not None:
            _WINDOWS[scenario.id] = dated
            return dated
    return span


def measures_its_own_price(
    quote: classification.Quote | None, cfg: ScenariosConfig | None = None
) -> bool:
    """True when this exact line has a price history reaching at least one episode.

    What the screen needs to say « mesurée » honestly: a line quoted on a venue
    we can read, whose history is old enough to have lived through a crisis.
    """
    if quote is None:
        return False
    c = cfg or config()
    return any(
        s.window is not None
        and episodes.measure(quote.ticker, "yahoo", quote.currency, window_of(s, c)) is not None
        for s in c.scenarios
    )


def measured_classes(cfg: ScenariosConfig | None = None) -> list[str]:
    """Classes measured on a real index in at least one episode."""
    c = cfg or config()
    seen: list[str] = []
    for scenario in c.scenarios:
        for asset_class in measured_returns(scenario, c):
            if asset_class not in seen:
                seen.append(asset_class)
    return seen


def pocket_return(
    pocket: Pocket, scenario: Scenario, measured: dict[str, float] | None = None
) -> float:
    """What this slice did, measured as finely as the sources allow."""
    return pocket_return_and_level(pocket, scenario, measured)[0]


def pocket_return_and_level(
    pocket: Pocket, scenario: Scenario, measured: dict[str, float] | None = None
) -> tuple[float, str]:
    """The figure and where it came from: 'line', 'index', 'declared' or 'borrowed'.

    Three levels, tried in order and none of them curated by hand: the line's
    own price when Yahoo has it back that far, the class's index when a
    registered series covers the window, the study's declared figure otherwise
    — or a neighbour's, for a class that declares none.
    """
    if pocket.quote is not None and scenario.window is not None:
        own = episodes.measure(
            pocket.quote.ticker, "yahoo", pocket.quote.currency, window_of(scenario)
        )
        if own is not None:
            return own, "line"
    borrows = config().fallback_class
    value = scenario.ret(pocket.asset_class, measured, borrows)
    if measured and pocket.asset_class in measured:
        return value, "index"
    if pocket.asset_class in scenario.returns:
        return value, "declared"
    return value, "borrowed"


def compute(wealth: Wealth) -> list[StressTestResult]:
    """Every scenario, worst loss first, in € and in % of the patrimony."""
    cfg = config()
    held = pockets(wealth, cfg)
    total = sum(p.amount for p in held)
    if total <= 0:
        return []
    # The lines held and the class indices Yahoo serves, in one round trip:
    # asked one by one they cost a call each, before the first scenario.
    episodes.prime(
        [p.quote.ticker for p in held if p.quote is not None]
        + [s.id for series in cfg.class_series.values() for s in series if s.provider == "yahoo"]
    )

    results: list[StressTestResult] = []
    for scenario in cfg.scenarios:
        measured = measured_returns(scenario, cfg)
        loss_eur = sum(p.amount * pocket_return(p, scenario, measured) for p in held)
        equity_eur = sum(p.amount for p in held if p.asset_class.startswith("equity_"))
        effect = scenario.currency_effect(measured)
        results.append(
            StressTestResult(
                id=scenario.id,
                label=scenario.label,
                description=scenario.description,
                start=scenario.start,
                end=scenario.end,
                pnl_pct=loss_eur / total,
                loss_eur=loss_eur,
                currency_effect_pct=effect,
                currency_effect_eur=effect * equity_eur if effect is not None else None,
            )
        )
    results.sort(key=lambda r: r.pnl_pct)
    logger.info(
        "stress: %d scenarios on %.0f € (%s)",
        len(results),
        total,
        ", ".join(f"{k} {v:.0f}" for k, v in sorted(_by_class(held).items())),
    )
    return results
