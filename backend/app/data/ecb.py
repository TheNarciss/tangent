"""ECB Data Portal — policy rate and official reference FX, no API key.

The portal answers SDMX; we ask for `format=csvdata`, which is a flat CSV with
one row per observation. Only two columns matter: TIME_PERIOD and OBS_VALUE.
"""

import io
import logging
from datetime import date

import pandas as pd

from ..errors import DataSourceError
from . import http
from .config import config

logger = logging.getLogger(__name__)


def series(key: str, *, start: date | None = None, last_n: int | None = None) -> pd.Series:
    """One ECB series (e.g. 'EXR/D.USD.EUR.SP00.A') as a float Series by date."""
    cfg = config()
    params: dict[str, str] = {"format": "csvdata"}
    if last_n is not None:
        params["lastNObservations"] = str(last_n)
    if start:
        params["startPeriod"] = start.isoformat()

    body = http.get_text(
        f"{cfg.ecb.base_url}/{key}", params=params, ttl_hours=cfg.cache_hours.macro
    )
    return _parse_csv(body, key)


def named(name: str, *, start: date | None = None, last_n: int | None = None) -> pd.Series:
    """A series declared in data_sources.yaml (e.g. 'policy_rate')."""
    cfg = config()
    key = cfg.ecb.series.get(name)
    if not key:
        raise DataSourceError(f"Série BCE inconnue dans data_sources.yaml: {name}")
    return series(key, start=start, last_n=last_n)


def _parse_csv(body: str, key: str) -> pd.Series:
    frame = pd.read_csv(io.StringIO(body))
    missing = {"TIME_PERIOD", "OBS_VALUE"} - set(frame.columns)
    if missing:
        raise DataSourceError(f"Réponse BCE inattendue pour {key}: colonnes {missing} absentes.")

    values = pd.to_numeric(frame["OBS_VALUE"], errors="coerce")
    out = pd.Series(values.to_numpy(), index=pd.to_datetime(frame["TIME_PERIOD"])).dropna()
    if out.empty:
        raise DataSourceError(f"Aucune observation exploitable pour {key}.")
    out.name = key
    return out.sort_index()
