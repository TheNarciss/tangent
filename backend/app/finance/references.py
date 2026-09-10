"""Long-run reference figures, for context rather than for calculation.

Two sources sat in `app/data`, tested and probed, feeding no screen at all
(ADR-024 built the layer; nothing consumed it). They each get one job here:

- **Shiller** answers « what is the worst a year of equities has ever been? »
  over 150 years, where Ken French only reaches 1990. Since 1871, the worst
  twelve months cost US equities **58 %** in real terms — eleven points worse
  than anything the post-1990 window contains.
- **Damodaran** answers « why hold equities at all? » with a century of
  realized returns for equities and for bonds.

Neither figure enters a computation: they sit next to the user's own numbers
so a verdict means something. When a source is unreachable, the value is
`None` and the screen simply says less — no fallback constant, because a
stale reference presented as a fact would be worse than no reference.
"""

import logging

from ..data import damodaran, shiller
from ..errors import DataSourceError
from . import analytics

logger = logging.getLogger(__name__)

# The column Shiller publishes as a level, deflated by his own CPI.
_SHILLER_SERIES = "real_total_return"
_EQUITIES = "equity_us"
_BONDS = "tbond_10y"


def worst_year_since_1871() -> tuple[float, int, int] | None:
    """(worst twelve months, first year, last year) for US equities, in real terms."""
    try:
        levels = shiller.series(_SHILLER_SERIES)
        monthly = levels.pct_change().dropna()
        worst = analytics.worst_rolling_year(monthly)
    except (DataSourceError, ValueError, KeyError):
        logger.warning("référence Shiller indisponible")
        return None
    return worst, int(levels.index[0].year), int(levels.index[-1].year)


def long_run_returns() -> dict[str, float | int] | None:
    """Annualised return of US equities and 10-year Treasuries since 1928."""
    try:
        equities = damodaran.annual_returns(_EQUITIES)
        bonds = damodaran.annual_returns(_BONDS)
    except (DataSourceError, ValueError, KeyError):
        logger.warning("référence Damodaran indisponible")
        return None
    return {
        "equities": _annualized(equities),
        "bonds": _annualized(bonds),
        "from_year": int(equities.index[0].year),
        "to_year": int(equities.index[-1].year),
    }


def _annualized(annual_returns) -> float:
    """Geometric mean of a series of annual returns."""
    return float((1.0 + annual_returns).prod() ** (1.0 / len(annual_returns)) - 1.0)
