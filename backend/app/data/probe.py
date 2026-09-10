"""Checks every external source and reports what it actually serves.

    python -m app.data.probe

Prints one line per source: status, coverage, last value, latency. This is how
we verify a source still answers and where its history really starts — no test
in CI hits the network, so this stays a manual command.

Yahoo Finance is probed too even though it lives in `finance/market.py`: it is
the least reliable source we depend on, so its state belongs in the same report.
"""

import logging
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import pandas as pd

from . import damodaran, ecb, eurostat, fred, ken_french, lbma, openfigi, shiller

logger = logging.getLogger(__name__)

# Amundi MSCI World UCITS ETF — a stable ISIN to check the reference layer.
SAMPLE_ISIN = "LU1681043599"


@dataclass(frozen=True)
class Probe:
    source: str
    label: str
    run: Callable[[], str]


@dataclass(frozen=True)
class Result:
    source: str
    label: str
    ok: bool
    detail: str
    millis: int


def _coverage(series: pd.Series, unit: str = "") -> str:
    """Coverage plus the age of the last point: a source can answer and still be stale."""
    first, last = series.index[0].date(), series.index[-1].date()
    age_days = (date.today() - last).days
    return (
        f"{first} → {last} (+{age_days}j, {len(series)} pts), dernier {series.iloc[-1]:.4g}{unit}"
    )


def _fred(name: str, unit: str) -> Callable[[], str]:
    return lambda: _coverage(fred.named(name), unit)


def _ecb(name: str, unit: str) -> Callable[[], str]:
    return lambda: _coverage(ecb.named(name), unit)


def _region(region: str) -> Callable[[], str]:
    def run() -> str:
        monthly = ken_french.monthly_returns(region)
        crash = ken_french.window_return(region, "2008-01", "2008-12")
        return f"{_coverage(monthly)} · 2008 : {crash:+.1%}"

    return run


def _eurostat() -> str:
    return f"{_coverage(eurostat.hicp_index())} · inflation a/a {eurostat.inflation_yoy():+.2%}"


def _metal(metal: str) -> Callable[[], str]:
    def run() -> str:
        quotes = lbma.price(metal, "EUR")
        crash = lbma.window_return(metal, "2008-01-01", "2008-12-31")
        return f"{_coverage(quotes, ' €')} · 2008 : {crash:+.1%}"

    return run


def _damodaran(asset_class: str) -> Callable[[], str]:
    def run() -> str:
        annual = damodaran.annual_returns(asset_class)
        crash = damodaran.window_return(asset_class, 2008, 2008)
        return f"{_coverage(annual)} · 2008 : {crash:+.1%}"

    return run


def _shiller() -> str:
    levels = shiller.series("real_total_return")
    seventies = shiller.window_return("real_total_return", "1973-01", "1974-12")
    return f"{_coverage(levels)} · 1973-74 réel : {seventies:+.1%}"


def _openfigi() -> str:
    records = openfigi.map_isins([SAMPLE_ISIN]).get(SAMPLE_ISIN, [])
    if not records:
        return "aucun enregistrement pour l'ISIN témoin"
    paris = openfigi.ticker_for(SAMPLE_ISIN, exchange_code="FP")
    return f"{len(records)} cotations, Paris → {paris}"


def _yahoo() -> str:
    from ..finance import market

    prices = market.fetch_prices(["CW8.PA"], period="1mo")
    return f"CW8.PA {len(prices)} séances, dernier {prices.iloc[-1, 0]:.2f}"


# Daily index series would let the stress tests replay a Nasdaq or a Europe
# fund on the exact dates of each episode, instead of lending it the amplitude
# of world equities. What matters is how far back each one goes: an index that
# starts in 2012 cannot replay 2000-03.
YAHOO_INDICES = {
    "^NDX": "Nasdaq-100",
    "^GSPC": "S&P 500",
    "^STOXX": "STOXX Europe 600",
    "^N225": "Nikkei 225",
    "EEM": "Émergents (ETF)",
    "URTH": "Monde (ETF)",
}


def _yahoo_index(ticker: str) -> Callable[[], str]:
    def run() -> str:
        from ..finance import market

        prices = market.fetch_prices([ticker], period="max").iloc[:, 0].dropna()
        first, last = prices.index[0].date(), prices.index[-1].date()
        return f"{first} → {last} ({len(prices)} séances), dernier {prices.iloc[-1]:.0f}"

    return run


PROBES: tuple[Probe, ...] = (
    Probe("fred", "OAT 10 ans France", _fred("oat_10y", " %")),
    Probe("fred", "EUR/USD", _fred("eur_usd", "")),
    Probe("fred", "IPC France", _fred("cpi_france", "")),
    Probe("ecb", "Taux directeur BCE", _ecb("policy_rate", " %")),
    Probe("ecb", "EUR/USD référence", _ecb("eur_usd", "")),
    Probe("eurostat", "IPC harmonisé France", _eurostat),
    *(Probe("ken_french", region, _region(region)) for region in ken_french.regions()),
    *(Probe("damodaran", c, _damodaran(c)) for c in damodaran.classes()),
    Probe("shiller", "S&P total return réel", _shiller),
    *(Probe("lbma", metal, _metal(metal)) for metal in lbma.metals()),
    Probe("openfigi", "ISIN → ticker", _openfigi),
    Probe("yahoo", "Cours quotidiens", _yahoo),
    *(Probe("yahoo", label, _yahoo_index(t)) for t, label in YAHOO_INDICES.items()),
)


def run_all() -> list[Result]:
    results: list[Result] = []
    for probe in PROBES:
        started = time.perf_counter()
        try:
            detail, ok = probe.run(), True
        except Exception as exc:  # a probe reports failures, it never raises
            detail, ok = str(exc), False
        millis = int((time.perf_counter() - started) * 1000)
        results.append(Result(probe.source, probe.label, ok, detail, millis))
    return results


def render(results: list[Result]) -> str:
    names = {r: f"{r.source}/{r.label}" for r in results}
    width = max(len(n) for n in names.values())
    lines = []
    for r in results:
        mark = "OK  " if r.ok else "FAIL"
        lines.append(f"{mark} {names[r]:<{width}}  {r.millis:>6} ms  {r.detail}")
    failed = [r for r in results if not r.ok]
    lines.append("")
    lines.append(f"{len(results) - len(failed)}/{len(results)} sources joignables.")
    return "\n".join(lines)


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    results = run_all()
    print(render(results))
    return 1 if any(not r.ok for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
