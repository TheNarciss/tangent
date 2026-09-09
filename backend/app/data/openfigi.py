"""OpenFIGI — ISIN to ticker, exchange and instrument name. No API key.

Free tier: 25 requests/minute, 10 ISINs per request. A free key would raise
that to 250/min; at a few lines per user we never come close, so we stay
anonymous (ADR-024).

This is the reference layer that lets the rest of the app stop guessing a
ticker from a Powens label.
"""

import logging
from typing import Any

from ..errors import DataSourceError
from . import http
from .config import config

logger = logging.getLogger(__name__)


def map_isins(isins: list[str]) -> dict[str, list[dict[str, Any]]]:
    """ISIN → list of instrument records (one per listing venue). Unknown ISINs map to []."""
    cfg = config()
    unique = [i.strip().upper() for i in dict.fromkeys(isins) if i and i.strip()]
    if not unique:
        return {}

    out: dict[str, list[dict[str, Any]]] = {}
    size = cfg.openfigi.max_isins_per_request
    for start in range(0, len(unique), size):
        batch = unique[start : start + size]
        payload = [{"idType": "ID_ISIN", "idValue": isin} for isin in batch]
        answer = http.post_json(cfg.openfigi.base_url, payload, ttl_hours=cfg.cache_hours.reference)
        out.update(_parse(batch, answer))
    return out


def ticker_for(isin: str, *, exchange_code: str | None = None) -> str | None:
    """Best ticker for an ISIN, optionally restricted to one venue (e.g. 'FP' for Paris)."""
    records = map_isins([isin]).get(isin.strip().upper(), [])
    if exchange_code:
        records = [r for r in records if r.get("exchCode") == exchange_code]
    for record in records:
        ticker = record.get("ticker")
        if ticker:
            return str(ticker)
    return None


def _parse(batch: list[str], answer: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(answer, list) or len(answer) != len(batch):
        raise DataSourceError("Réponse OpenFIGI de taille inattendue.")

    out: dict[str, list[dict[str, Any]]] = {}
    for isin, entry in zip(batch, answer, strict=True):
        if isinstance(entry, dict) and isinstance(entry.get("data"), list):
            out[isin] = entry["data"]
        else:
            # OpenFIGI answers {"warning": "No identifier found."} for an unknown ISIN.
            out[isin] = []
    return out
