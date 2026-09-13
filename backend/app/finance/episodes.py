"""Measure what an asset class actually did during a crisis, when a series exists.

The stress tests used to carry one hand-copied number per class and per
episode. That does not scale: adding a class meant recomputing ten figures by
hand, and a class without a figure silently borrowed the amplitude of world
equities — which understated a Nasdaq tracker by thirty points on the dot-com
crash.

This module replaces the copying with a loop. For a class that declares an
index series in `stress_scenarios.yaml`, and an episode whose window the series
covers, it measures the return **from one end of the window to the other**, and
converts it to euros at the ECB rate of those two days.

Why end-to-end and not each class's own peak-to-trough: a stress test asks what
one patrimony did over one period. Classes do not bottom on the same day — gold
had its worst moment in October 2008, equities in March 2009 — so summing each
class's own worst moment would describe a day that never happened. The windows
are already the crisis: for world equities, whose peak and trough define them,
end-to-end *is* the peak-to-trough of the study's own figures.

Anything else falls back to the declared value: a series that does not reach
1990, a provider that does not answer, a class nobody has mapped yet.
"""

import logging
from datetime import date, datetime, timedelta

import pandas as pd

from ..data import ecb, fred, ken_french, lbma
from ..errors import AppError, DataSourceError

logger = logging.getLogger(__name__)

# The euro did not exist before 1999: an older episode is measured in the
# index's own currency, and the scenario file says so.
_EURO_FROM = date(1999, 1, 4)


# A series may start a few days after the window opens (a holiday, a weekend)
# and still cover the episode. Any later and it is a series born *during* the
# crisis, which would report only the part it saw.
_GRACE = pd.Timedelta(days=7)


def measure(
    series_id: str,
    provider: str,
    currency: str,
    window: tuple[str, str],
    *,
    in_euros: bool = True,
) -> float | None:
    """Return from one end of the window to the other, in euros. None when unmeasurable.

    `in_euros=False` keeps the move in the series' own currency: what a local
    investor saw, which the screen sets against the euro figure to show what
    the exchange rate cost or paid.
    """
    try:
        levels = _levels(provider, series_id, currency)
    except DataSourceError:
        logger.warning("série %s indisponible", series_id)
        return None
    if levels is None or len(levels) < 2:
        return None

    since, until = pd.Timestamp(window[0]), pd.Timestamp(window[1])
    if levels.index[0] > since + _GRACE or levels.index[-1] < until - _GRACE:
        return None  # the series does not cover the whole episode

    inside = levels.loc[since:until]
    if len(inside) < 2:
        return None

    first_day, last_day = inside.index[0], inside.index[-1]
    move = float(inside.iloc[-1] / inside.iloc[0] - 1.0)
    if currency == "EUR" or not in_euros:
        return move
    return _in_euros(move, first_day, last_day, currency)


def peak_to_trough(
    series_id: str, provider: str, currency: str, span: tuple[str, str]
) -> tuple[str, str] | None:
    """The crisis's own dates: the deepest fall of the series inside the span, in euros.

    Hand-typed month boundaries missed the trough by weeks — March 2009 ended
    fifteen points above its 9th. The dates come from the series instead, and
    every class is then measured between the same two days.
    """
    try:
        levels = _levels(provider, series_id, currency)
    except DataSourceError:
        return None
    if levels is None or len(levels) < 2:
        return None
    if currency != "EUR":
        levels = _euro_levels(levels, currency)
        if levels is None:
            return None

    inside = levels.loc[pd.Timestamp(span[0]) : pd.Timestamp(span[1])]
    if len(inside) < 2:
        return None
    drawdown = inside / inside.cummax() - 1.0
    trough = drawdown.idxmin()
    if drawdown[trough] >= 0:
        return None  # the series never fell inside the span
    peak = inside.loc[:trough].idxmax()
    return str(peak.date()), str(trough.date())


def _euro_levels(levels: pd.Series, currency: str) -> pd.Series | None:
    """The same levels seen by a euro investor, day by day. None before the euro."""
    if levels.index[0].date() < _EURO_FROM:
        levels = levels.loc[pd.Timestamp(_EURO_FROM) :]
    if len(levels) < 2:
        return None
    try:
        rates = ecb.named(f"eur_{currency.lower()}")
    except DataSourceError:
        return None
    aligned = rates.reindex(levels.index, method="ffill").dropna()
    return (levels.loc[aligned.index] / aligned).astype(float)


def _levels(provider: str, series_id: str, currency: str) -> pd.Series | None:
    """The provider's daily series. None for a provider nobody has taught us."""
    if provider == "fred":
        return fred.series(series_id)
    if provider == "lbma":
        return lbma.price(series_id, currency)
    if provider == "yahoo":
        return _quoted(series_id)
    if provider == "ken_french":
        # Daily total returns, compounded into a level series: what 1 dollar
        # invested on the first session was worth on each later one.
        return (1.0 + ken_french.daily_returns(series_id)).cumprod()
    logger.warning("fournisseur de série inconnu: %s", provider)
    return None


# Ten episodes ask the same line for its history ten times. Successful fetches
# are already cached by `market`, but a silence is not — and a portfolio of
# twenty lines Yahoo cannot serve would spend two hundred failed calls before
# drawing the screen. So the answer is remembered either way.
_QUOTED: dict[str, tuple[datetime, pd.Series | None]] = {}
_QUOTED_TTL = timedelta(hours=1)


def prime(tickers: list[str]) -> None:
    """Fetch several lines in one round trip, so a page costs one call, not one per line.

    Best effort: a batch Yahoo rejects (one delisted symbol fails the whole
    download) is simply not primed, and each line is then asked for on its own.
    """
    from . import market

    wanted = [t for t in dict.fromkeys(tickers) if _fresh(t) is None]
    if not wanted:
        return
    try:
        prices = market.fetch_prices(wanted, period="max")
    except AppError:
        return
    now = datetime.now()
    for ticker in wanted:
        if ticker in prices.columns:
            _QUOTED[ticker] = (now, prices[ticker].dropna())


def _fresh(ticker: str) -> tuple[datetime, pd.Series | None] | None:
    cached = _QUOTED.get(ticker)
    if cached and datetime.now() - cached[0] < _QUOTED_TTL:
        return cached
    return None


def _quoted(ticker: str) -> pd.Series | None:
    """One line's own price history. None when Yahoo does not know it.

    Yahoo has no service contract, so every failure is a fallback rather than
    an error: the caller measures the asset class instead, and the screen still
    answers.
    """
    from . import market

    cached = _fresh(ticker)
    if cached:
        return cached[1]

    levels: pd.Series | None
    try:
        levels = market.fetch_prices([ticker], period="max").iloc[:, 0].dropna()
    except AppError:
        logger.info("pas d'historique Yahoo pour %s", ticker)
        levels = None
    _QUOTED[ticker] = (datetime.now(), levels)
    return levels


def _in_euros(
    move: float, first_day: pd.Timestamp, last_day: pd.Timestamp, currency: str
) -> float | None:
    """Convert a foreign return to what a euro investor saw, at the ECB rate of those days.

    A euro that buys more dollars at the end than at the start softens a fall;
    the reverse deepens it. Before 1999 there is no rate to apply, and a
    currency the ECB does not publish gets no rate either — in both cases the
    caller keeps the declared figure rather than pretending the move was free.
    """
    if first_day.date() < _EURO_FROM:
        return None
    try:
        rates = ecb.named(f"eur_{currency.lower()}")
        at_first = rates.loc[:first_day].iloc[-1]
        at_last = rates.loc[:last_day].iloc[-1]
    except (DataSourceError, KeyError, IndexError):
        logger.warning("cours EUR/%s indisponible, épisode non mesuré", currency)
        return None
    return (1.0 + move) * float(at_first / at_last) - 1.0
