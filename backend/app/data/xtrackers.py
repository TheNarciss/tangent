"""Index constituents, read from the daily holdings file of an Xtrackers ETF.

An index fund must hold the index: its published holdings *are* the current
constituents, refreshed every trading day by the fund's administrator. DWS
exposes one CSV per share class, without key or cookie, with the ISIN, name,
country, currency, weight and main exchange of every line. The file is the
source of truth: nothing is copied into the repository, and a company that
enters or leaves the index appears or disappears at the next fetch.

STOXX itself no longer publishes component files, and the exchanges' own
pages are either encrypted or empty to a script; the fund's file is the
plainest self-updating source there is.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass

from ..errors import DataSourceError
from . import http
from .config import config

logger = logging.getLogger(__name__)

_ISIN = "Constituent ISIN"
_NAME = "Constituent Name"
_CURRENCY = "Constituent Currency ISO Code"
_WEIGHT = "Constituent Weighting"
_EXCHANGE = "Constituent Main Exchange Name"
_REQUIRED = (_ISIN, _NAME, _CURRENCY, _WEIGHT)

# The fund's exchange names, in OpenFIGI's venue codes. Mechanical, no judgement.
EXCHANGE_CODES: dict[str, str] = {
    "Euronext Paris": "FP",
    "Euronext Amsterdam": "NA",
    "XETRA": "GR",
    "Milan Stock Exchange": "IM",
    "Mercado Continuo Espana": "SM",
    "Euronext Brussels": "BB",
    "Euronext Lisbon": "PL",
    "Helsinki Stock Exchange": "FH",
    "Vienna Stock Exchange": "AV",
    "Irish Stock Exchange": "ID",
}


@dataclass(frozen=True)
class Constituent:
    isin: str
    name: str
    currency: str
    weight: float
    exchange: str  # as the fund names it; may be empty for a fresh listing

    @property
    def venue(self) -> str | None:
        """The main exchange as an OpenFIGI code, when the fund names one we know."""
        return EXCHANGE_CODES.get(self.exchange)


def funds() -> list[str]:
    """Fund keys declared in data_sources.yaml."""
    return list(config().xtrackers.funds)


def constituents(fund: str) -> list[Constituent]:
    """Current lines of the fund, as its holdings file lists them today."""
    cfg = config()
    share_class = cfg.xtrackers.funds.get(fund)
    if not share_class:
        raise DataSourceError(f"Fonds inconnu dans data_sources.yaml: {fund}")
    url = f"{cfg.xtrackers.base_url}/{share_class}/"
    text = http.get_text(url, ttl_hours=cfg.cache_hours.macro)
    lines = parse(text)
    if not lines:
        raise DataSourceError(f"Aucun constituant dans le fichier Xtrackers de {share_class}.")
    return lines


def parse(text: str) -> list[Constituent]:
    """The rows of the semicolon-separated holdings file, by column name."""
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    missing = [c for c in _REQUIRED if c not in (reader.fieldnames or [])]
    if missing:
        raise DataSourceError(f"Fichier Xtrackers réorganisé, colonnes absentes: {missing}")
    out: list[Constituent] = []
    for row in reader:
        isin = (row.get(_ISIN) or "").strip().upper()
        if not isin:
            continue
        try:
            weight = float(row.get(_WEIGHT) or 0.0)
        except ValueError:
            weight = 0.0
        out.append(
            Constituent(
                isin=isin,
                name=(row.get(_NAME) or "").strip(),
                currency=(row.get(_CURRENCY) or "").strip().upper(),
                weight=weight,
                exchange=(row.get(_EXCHANGE) or "").strip(),
            )
        )
    return out
