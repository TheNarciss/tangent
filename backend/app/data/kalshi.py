"""Kalshi: the regulated prediction market, read for its economic series.

Market data is public without a key: a series (« Fed meeting », « CPI »)
holds events (one per meeting or month), an event holds markets (one per
outcome), each quoting a yes-price between 0 and 1 that reads as a
probability. Volume and open interest are in contracts of one dollar.
Kalshi does not say how far a price moved: the caller remembers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..errors import DataSourceError
from . import http
from .config import config

_PAGE = 200  # the API's ceiling per call


@dataclass(frozen=True)
class Market:
    ticker: str
    event_ticker: str
    series_ticker: str
    title: str
    yes_price: float  # 0..1
    volume_24h: float  # contracts, one dollar each
    open_interest: float
    close_time: str  # ISO, may be empty

    @property
    def url(self) -> str:
        return f"https://kalshi.com/markets/{self.series_ticker.lower()}"


def markets(series_ticker: str, *, ttl_hours: float = 1.0) -> list[Market]:
    """Every open market of the series, page after page."""
    cfg = config().kalshi
    out: list[Market] = []
    cursor = ""
    while True:
        params = {"series_ticker": series_ticker, "status": "open", "limit": str(_PAGE)}
        if cursor:
            params["cursor"] = cursor
        body = http.get_text(f"{cfg.base_url}/markets", params=params, ttl_hours=ttl_hours)
        page, cursor = parse_markets(body, series_ticker)
        out.extend(page)
        if not cursor or len(page) < _PAGE:
            return out


def parse_markets(body: str, series_ticker: str) -> tuple[list[Market], str]:
    """The page's markets and the cursor of the next one, empty on the last."""
    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise DataSourceError(f"Réponse Kalshi illisible: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("markets"), list):
        raise DataSourceError("Réponse Kalshi inattendue (markets attendu).")
    out: list[Market] = []
    for m in payload["markets"]:
        if not isinstance(m, dict) or not m.get("ticker"):
            continue
        price = _num(m.get("last_price_dollars"))
        if price <= 0:
            # Never traded: the mid of the book, when there is one.
            bid, ask = _num(m.get("yes_bid_dollars")), _num(m.get("yes_ask_dollars"))
            price = round((bid + ask) / 2, 4) if bid and ask else 0.0
        out.append(
            Market(
                ticker=str(m["ticker"]),
                event_ticker=str(m.get("event_ticker") or ""),
                series_ticker=series_ticker,
                title=str(m.get("title") or ""),
                yes_price=price,
                volume_24h=_num(m.get("volume_24h_fp")),
                open_interest=_num(m.get("open_interest_fp")),
                close_time=str(m.get("close_time") or ""),
            )
        )
    return out, str(payload.get("cursor") or "")


def _num(raw: Any) -> float:
    try:
        return float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0
