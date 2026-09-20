"""CFTC Commitments of Traders: what large futures traders hold, every Tuesday.

Two public datasets on the CFTC's open-data portal, keyless: financial
futures (S&P 500, Treasuries, currencies) split by dealer, asset manager and
leveraged fund; commodities (gold, oil…) split by producer, swap dealer and
managed money. One row per contract and week, published Friday for the
Tuesday. Read here: the speculators' side — leveraged funds on the first,
managed money on the second — long, short, and the contract's open interest.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..errors import DataSourceError
from . import http
from .config import config

# Column names differ between the two reports; the meaning is the same.
_COLUMNS = {
    "financial": ("lev_money_positions_long", "lev_money_positions_short"),
    "commodities": ("m_money_positions_long_all", "m_money_positions_short_all"),
}
_DATE = "report_date_as_yyyy_mm_dd"
_OPEN_INTEREST = "open_interest_all"


@dataclass(frozen=True)
class Week:
    day: str  # YYYY-MM-DD, the Tuesday the positions are counted
    spec_long: float
    spec_short: float
    open_interest: float

    @property
    def net_share(self) -> float:
        """Speculators' net position as a share of open interest, -1..1."""
        return (
            (self.spec_long - self.spec_short) / self.open_interest if self.open_interest else 0.0
        )


def positions(dataset: str, contract: str, *, weeks: int, ttl_hours: float = 12.0) -> list[Week]:
    """The contract's last `weeks` rows, newest first."""
    cfg = config().cftc
    if dataset not in _COLUMNS:
        raise DataSourceError(f"Rapport CFTC inconnu: {dataset}")
    resource = cfg.financial_dataset if dataset == "financial" else cfg.commodities_dataset
    long_col, short_col = _COLUMNS[dataset]
    params = {
        "$select": ",".join((_DATE, long_col, short_col, _OPEN_INTEREST)),
        "$where": f"contract_market_name='{contract}'",
        "$order": f"{_DATE} DESC",
        "$limit": str(weeks),
    }
    body = http.get_text(f"{cfg.base_url}/{resource}.json", params=params, ttl_hours=ttl_hours)
    return parse_positions(body, dataset)


def parse_positions(body: str, dataset: str) -> list[Week]:
    long_col, short_col = _COLUMNS[dataset]
    try:
        rows = json.loads(body)
    except ValueError as exc:
        raise DataSourceError(f"Réponse CFTC illisible: {exc}") from exc
    if not isinstance(rows, list):
        raise DataSourceError("Réponse CFTC inattendue (liste attendue).")
    out: list[Week] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        day = str(row.get(_DATE) or "")[:10]
        # The same contract can be listed twice a week (two exchanges): keep the first.
        if not day or day in seen:
            continue
        try:
            week = Week(
                day=day,
                spec_long=_num(row.get(long_col)),
                spec_short=_num(row.get(short_col)),
                open_interest=_num(row.get(_OPEN_INTEREST)),
            )
        except ValueError:
            continue
        seen.add(day)
        out.append(week)
    out.sort(key=lambda w: w.day, reverse=True)
    return out


def _num(raw: Any) -> float:
    return float(raw) if raw not in (None, "") else 0.0
