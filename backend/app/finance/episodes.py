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
from datetime import date

import pandas as pd

from ..data import ecb, fred, lbma
from ..errors import DataSourceError

logger = logging.getLogger(__name__)

# The euro did not exist before 1999: an older episode is measured in the
# index's own currency, and the scenario file says so.
_EURO_FROM = date(1999, 1, 4)


def measure(series_id: str, provider: str, currency: str, window: tuple[str, str]) -> float | None:
    """Peak-to-trough return inside the window, in euros. None when unmeasurable."""
    try:
        levels = _levels(provider, series_id, currency)
    except DataSourceError:
        logger.warning("série %s indisponible", series_id)
        return None
    if levels is None:
        return None

    inside = levels.loc[window[0] : window[1]]
    if len(inside) < 2:
        return None  # the series does not reach this episode

    first_day, last_day = inside.index[0], inside.index[-1]
    move = float(inside.iloc[-1] / inside.iloc[0] - 1.0)
    if currency == "EUR":
        return move
    return _in_euros(move, first_day, last_day)


def _levels(provider: str, series_id: str, currency: str) -> pd.Series | None:
    """The provider's daily series. None for a provider nobody has taught us."""
    if provider == "fred":
        return fred.series(series_id)
    if provider == "lbma":
        return lbma.price(series_id, currency)
    logger.warning("fournisseur de série inconnu: %s", provider)
    return None


def _in_euros(move: float, first_day: pd.Timestamp, last_day: pd.Timestamp) -> float | None:
    """Convert a dollar return to what a euro investor saw, at the ECB rate of those days.

    A euro that buys more dollars at the end than at the start softens a fall;
    the reverse deepens it. Before 1999 there is no rate to apply, and the
    caller keeps the declared figure in its own currency.
    """
    if first_day.date() < _EURO_FROM:
        return None
    try:
        rates = ecb.named("eur_usd")
        at_first = rates.loc[:first_day].iloc[-1]
        at_last = rates.loc[:last_day].iloc[-1]
    except (DataSourceError, IndexError):
        logger.warning("cours EUR/USD indisponible, rendement laissé en devise")
        return None
    return (1.0 + move) * float(at_first / at_last) - 1.0
