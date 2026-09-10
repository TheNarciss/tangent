"""Measure what an asset class actually did during a crisis, when a series exists.

The stress tests used to carry one hand-copied number per class and per
episode. That does not scale: adding a class meant recomputing ten figures by
hand, and a class without a figure silently borrowed the amplitude of world
equities — which understated a Nasdaq tracker by thirty points on the dot-com
crash.

This module replaces the copying with a loop. For a class that declares an
index series in `stress_scenarios.yaml`, and an episode whose window the series
covers, it measures the **peak-to-trough fall inside the window** and converts
it to euros at the ECB rate of the two days it picked — exactly the method
behind the study's own figures.

Anything else falls back to the declared value: a series that does not reach
1990, a provider that does not answer, a class nobody has mapped yet.
"""

import logging
from datetime import date

import pandas as pd

from ..data import ecb, fred
from ..errors import DataSourceError

logger = logging.getLogger(__name__)

# The euro did not exist before 1999: an older episode is measured in the
# index's own currency, and the scenario file says so.
_EURO_FROM = date(1999, 1, 4)


def measure(series_id: str, provider: str, currency: str, window: tuple[str, str]) -> float | None:
    """Peak-to-trough return inside the window, in euros. None when unmeasurable."""
    if provider != "fred":
        logger.warning("fournisseur de série inconnu: %s", provider)
        return None
    try:
        levels = fred.series(series_id)
    except DataSourceError:
        logger.warning("série %s indisponible", series_id)
        return None

    inside = levels.loc[window[0] : window[1]]
    if len(inside) < 2:
        return None  # the series does not reach this episode

    peak_day, trough_day = _peak_to_trough(inside)
    fall = float(inside.loc[trough_day] / inside.loc[peak_day] - 1.0)
    if currency == "EUR":
        return fall
    return _in_euros(fall, peak_day, trough_day)


def _peak_to_trough(levels: pd.Series) -> tuple[pd.Timestamp, pd.Timestamp]:
    """The two days of the deepest fall: the trough, and the high that precedes it."""
    drawdown = levels / levels.cummax() - 1.0
    trough_day = drawdown.idxmin()
    peak_day = levels.loc[:trough_day].idxmax()
    return peak_day, trough_day


def _in_euros(fall: float, peak_day: pd.Timestamp, trough_day: pd.Timestamp) -> float | None:
    """Convert a dollar return to what a euro investor saw, at the ECB rate of those days.

    A euro that buys more dollars at the trough than at the peak softens the
    fall; the reverse deepens it. Before 1999 there is no rate to apply, and
    the caller keeps the figure in its own currency.
    """
    if peak_day.date() < _EURO_FROM:
        return None
    try:
        rates = ecb.named("eur_usd")
        at_peak = rates.loc[:peak_day].iloc[-1]
        at_trough = rates.loc[:trough_day].iloc[-1]
    except (DataSourceError, IndexError):
        logger.warning("cours EUR/USD indisponible, rendement laissé en devise")
        return None
    return (1.0 + fall) * float(at_peak / at_trough) - 1.0
