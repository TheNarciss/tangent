"""Index constituents, read from the Wikipedia page of each index.

STOXX no longer publishes its component files; the English Wikipedia pages of
the large European indices carry a sortable table with a « Ticker » column
already in Yahoo's notation (`AI.PA`, `ADS.DE`, `ASML.AS`). The page is the
source of truth: nothing is copied into the repository, and a company that
enters or leaves an index appears or disappears at the next fetch.

Only euro-quoted venues are kept — a euro investor's momentum has no exchange
rate inside it — and Yahoo's suffixes name them.
"""

from __future__ import annotations

import html
import logging
import re

from ..errors import DataSourceError
from . import http
from .config import config

logger = logging.getLogger(__name__)

_TABLE = re.compile(r"<table[^>]*>(.*?)</table>", re.S)
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_HEAD = re.compile(r"<th[^>]*>(.*?)</th>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_TAGS = re.compile(r"<[^>]+>")

# Euro venues, in Yahoo's notation.
TICKER = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,9}\.(PA|DE|AS|MI|MC|BR|LS)$")


def indices() -> list[str]:
    """Index keys declared in data_sources.yaml."""
    return list(config().wikipedia.indices)


def constituents(index: str) -> list[str]:
    """Yahoo tickers of the index's current members, as its Wikipedia page lists them."""
    cfg = config()
    page = cfg.wikipedia.indices.get(index)
    if not page:
        raise DataSourceError(f"Indice inconnu dans data_sources.yaml: {index}")
    text = http.get_text(f"{cfg.wikipedia.base_url}/{page}", ttl_hours=cfg.cache_hours.reference)
    tickers = parse_tickers(text)
    if not tickers:
        raise DataSourceError(f"Aucun tableau de constituants avec une colonne Ticker sur {page}.")
    return tickers


def parse_tickers(page: str) -> list[str]:
    """The tickers of the first table whose header has a « Ticker » column."""
    for table in _TABLE.findall(page):
        heads = [_clean(h) for h in _HEAD.findall(table)]
        column = next((i for i, h in enumerate(heads) if h.lower().startswith("ticker")), None)
        if column is None:
            continue
        out: list[str] = []
        for row in _ROW.findall(table):
            cells = [_clean(c) for c in _CELL.findall(row)]
            if column < len(cells) and TICKER.match(cells[column]):
                out.append(cells[column])
        if out:
            return out
    return []


def _clean(cell: str) -> str:
    return html.unescape(_TAGS.sub("", cell)).replace("\xa0", " ").strip()
