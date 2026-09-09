"""LBMA — official gold and silver fixings, no API key.

The London Bullion Market Association publishes its own fixings as flat JSON:
one entry per session, `d` the date and `v` the prices in USD, GBP and EUR, in
that order. Gold goes back to 1968, which covers every crisis we replay.

The euro leg is null before 1999 (the currency did not exist): asking for EUR
on an older window returns fewer points, it does not fail.
"""

import json
import logging

import pandas as pd

from ..errors import DataSourceError
from . import http
from .config import config

logger = logging.getLogger(__name__)

CURRENCIES = ("USD", "GBP", "EUR")


def metals() -> list[str]:
    """Metal keys available in data_sources.yaml (e.g. 'gold', 'silver')."""
    return list(config().lbma.series)


def price(metal: str, currency: str = "EUR") -> pd.Series:
    """Daily fixing of the metal in that currency, indexed by date."""
    cfg = config()
    series = cfg.lbma.series.get(metal)
    if not series:
        raise DataSourceError(f"Métal inconnu dans data_sources.yaml: {metal}")
    if currency not in CURRENCIES:
        raise DataSourceError(f"Devise LBMA inconnue: {currency} (attendu {CURRENCIES}).")

    body = http.get_text(f"{cfg.lbma.base_url}/{series}.json", ttl_hours=cfg.cache_hours.macro)
    return _parse(body, metal, CURRENCIES.index(currency))


def window_return(metal: str, start: str, end: str, currency: str = "EUR") -> float:
    """Return of the metal between two dates, inclusive. Dates are 'YYYY-MM-DD' or 'YYYY-MM'."""
    quotes = price(metal, currency).loc[start:end]
    if len(quotes) < 2:
        raise DataSourceError(f"Moins de deux cotations {metal} entre {start} et {end}.")
    return float(quotes.iloc[-1] / quotes.iloc[0] - 1.0)


def _parse(body: str, metal: str, position: int) -> pd.Series:
    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise DataSourceError(f"Réponse LBMA illisible pour {metal}: {exc}") from exc
    if not isinstance(payload, list):
        raise DataSourceError(f"Réponse LBMA inattendue pour {metal}.")

    dates: list[str] = []
    values: list[float] = []
    for entry in payload:
        quotes = entry.get("v") if isinstance(entry, dict) else None
        if not isinstance(quotes, list) or len(quotes) <= position:
            continue
        quote = quotes[position]
        if quote is None:  # euro leg before 1999
            continue
        dates.append(entry["d"])
        values.append(float(quote))

    if not dates:
        raise DataSourceError(f"Aucune cotation exploitable pour {metal}.")

    out = pd.Series(values, index=pd.to_datetime(dates)).sort_index()
    out.name = metal
    return out
