"""FRED (Federal Reserve Bank of St. Louis) — macro series, no API key.

`fredgraph.csv` serves any series as CSV without authentication, which is why
we use it rather than the JSON API (that one needs a key for nothing more).

Scope limit, deliberate: FRED's equity and bond index series are capped by
licence (S&P 500 to 10 years, ICE BofA to 3). We take rates, FX and inflation
here; long index history comes from `ken_french`.
"""

import io
import logging
from datetime import date

import pandas as pd

from ..errors import DataSourceError
from . import http
from .config import config

logger = logging.getLogger(__name__)


def series(series_id: str, *, start: date | None = None) -> pd.Series:
    """One FRED series as a float Series indexed by date. Missing points dropped."""
    cfg = config()
    params = {"id": series_id}
    if start:
        params["cosd"] = start.isoformat()

    body = http.get_text(cfg.fred.base_url, params=params, ttl_hours=cfg.cache_hours.macro)
    return _parse_csv(body, series_id)


def named(name: str, *, start: date | None = None) -> pd.Series:
    """A series declared in data_sources.yaml (e.g. 'oat_10y')."""
    cfg = config()
    series_id = cfg.fred.series.get(name)
    if not series_id:
        raise DataSourceError(f"Série FRED inconnue dans data_sources.yaml: {name}")
    return series(series_id, start=start)


def _parse_csv(body: str, series_id: str) -> pd.Series:
    frame = pd.read_csv(io.StringIO(body))
    if frame.empty or len(frame.columns) < 2:
        raise DataSourceError(f"FRED a renvoyé une série vide pour {series_id}.")

    date_col, value_col = frame.columns[0], frame.columns[1]
    # FRED writes "." for a missing observation.
    values = pd.to_numeric(frame[value_col], errors="coerce")
    out = pd.Series(values.to_numpy(), index=pd.to_datetime(frame[date_col])).dropna()
    if out.empty:
        raise DataSourceError(f"Aucune observation exploitable pour {series_id}.")
    out.name = series_id
    return out
