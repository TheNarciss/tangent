"""Eurostat — harmonised consumer price index for France, no API key.

Answers JSON-stat: `value` maps a flat position to a number, and
`dimension.time.category.index` maps a period label to that same position.
"""

import json
import logging

import pandas as pd

from ..errors import DataSourceError
from . import http
from .config import config

logger = logging.getLogger(__name__)


def hicp_index() -> pd.Series:
    """Monthly HICP index for France (base 2015 = 100), indexed by period."""
    cfg = config()
    hicp = cfg.eurostat.hicp
    params = {
        "format": "JSON",
        "geo": hicp.geo,
        "coicop": hicp.coicop,
        "unit": hicp.unit,
    }
    body = http.get_text(
        f"{cfg.eurostat.base_url}/{hicp.dataset}",
        params=params,
        ttl_hours=cfg.cache_hours.macro,
    )
    return _parse_jsonstat(body)


def inflation_yoy() -> float:
    """Year-on-year inflation from the HICP index, as a fraction (0.021 = 2,1 %).

    Looks up the same month one year earlier by date, not by position: the
    series can miss a month, and a positional offset would then compare two
    periods that are not twelve months apart.
    """
    index = hicp_index()
    last = index.index[-1]
    year_ago = last - pd.DateOffset(years=1)
    if year_ago not in index.index:
        raise DataSourceError(
            f"Historique IPC trop court : pas d'observation en {year_ago.date()}."
        )
    return float(index.iloc[-1] / index.loc[year_ago] - 1.0)


def _parse_jsonstat(body: str) -> pd.Series:
    try:
        payload = json.loads(body)
        positions = payload["dimension"]["time"]["category"]["index"]
        values = payload["value"]
    except (ValueError, KeyError, TypeError) as exc:
        raise DataSourceError(f"Réponse Eurostat inattendue: {exc}") from exc

    points = {
        period: float(values[str(pos)]) for period, pos in positions.items() if str(pos) in values
    }
    if not points:
        raise DataSourceError("Eurostat n'a renvoyé aucune observation.")

    out = pd.Series(points)
    out.index = pd.to_datetime(out.index)
    out.name = "hicp"
    return out.sort_index()
