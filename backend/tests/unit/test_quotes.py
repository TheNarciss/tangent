"""One line's own price: the scales, the cache, the name search, the ISIN fallback."""

from __future__ import annotations

from typing import ClassVar

import pandas as pd
import pytest

from app.errors import TickerNotFoundError
from app.finance import classification, market
from app.routers import quotes as quotes_router


@pytest.fixture(autouse=True)
def _cold():
    market._HISTORY.clear()
    market._SEARCH.clear()
    yield
    market._HISTORY.clear()
    market._SEARCH.clear()


class _FakeTicker:
    calls: ClassVar[list[tuple[str, str, str]]] = []
    bars: ClassVar[pd.DataFrame] = pd.DataFrame()
    meta: ClassVar[dict] = {}

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.history_metadata: dict = {}

    def history(self, period: str, interval: str, auto_adjust: bool) -> pd.DataFrame:
        _FakeTicker.calls.append((self.symbol, period, interval))
        self.history_metadata = dict(_FakeTicker.meta)
        return _FakeTicker.bars


def _bars(closes: list[float | None]) -> pd.DataFrame:
    index = pd.date_range("2026-09-21 09:00", periods=len(closes), freq="5min", tz="Europe/Paris")
    return pd.DataFrame({"Close": closes, "Volume": [0] * len(closes)}, index=index)


def test_history_reads_the_closes_and_the_metadata_once_per_scale(monkeypatch):
    _FakeTicker.calls = []
    _FakeTicker.bars = _bars([100.0, None, 101.5])
    _FakeTicker.meta = {
        "symbol": "AI.PA",
        "currency": "EUR",
        "longName": "L'Air Liquide S.A.",
        "chartPreviousClose": 99.0,
    }
    monkeypatch.setattr(market.yf, "Ticker", _FakeTicker)

    first = market.history("ai.pa", "1d")

    assert first.symbol == "AI.PA"
    assert first.name == "L'Air Liquide S.A."
    assert first.currency == "EUR"
    assert first.interval == "5m"
    assert first.previous_close == 99.0
    assert [p.close for p in first.points] == [100.0, 101.5]  # the empty bar is dropped
    assert first.points[0].t == "2026-09-21T09:00:00+02:00"

    assert market.history("ai.pa", "1d") is first  # served from the cache
    market.history("ai.pa", "5y")
    assert _FakeTicker.calls == [("ai.pa", "1d", "5m"), ("ai.pa", "5y", "1wk")]


def test_history_refuses_an_unknown_symbol_or_scale(monkeypatch):
    _FakeTicker.bars = _bars([])
    _FakeTicker.meta = {}
    monkeypatch.setattr(market.yf, "Ticker", _FakeTicker)

    with pytest.raises(TickerNotFoundError):
        market.history("NOPE.XX", "1y")
    with pytest.raises(TickerNotFoundError):
        market.history("AI.PA", "2y")


def test_search_lists_listed_instruments_only():
    raw = [
        {
            "symbol": "AI.PA",
            "longname": "L'Air Liquide S.A.",
            "exchDisp": "Paris",
            "quoteType": "EQUITY",
        },
        {"symbol": "EURUSD=X", "shortname": "EUR/USD", "quoteType": "CURRENCY"},
        {
            "symbol": "CW8.PA",
            "shortname": "AMUNDI MSCI WORLD",
            "exchange": "PAR",
            "quoteType": "ETF",
        },
        {"symbol": "^FCHI", "shortname": "CAC 40", "exchDisp": "Paris", "quoteType": "INDEX"},
        {"symbol": "NONAME", "quoteType": "EQUITY"},
    ]

    matches = market.parse_search(raw, limit=2)

    assert [(m.symbol, m.name, m.exchange, m.kind) for m in matches] == [
        ("AI.PA", "L'Air Liquide S.A.", "Paris", "equity"),
        ("CW8.PA", "AMUNDI MSCI WORLD", "PAR", "etf"),
    ]


def test_search_answers_empty_when_yahoo_fails(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("429")

    monkeypatch.setattr(market.yf, "Search", boom)
    assert market.search("  air   liquide ") == []
    assert market.search("") == []


def test_the_route_falls_back_on_the_isin_when_the_bank_ticker_is_unknown(monkeypatch):
    asked: list[str] = []

    def fake_history(symbol: str, scale: str) -> market.History:
        asked.append(symbol)
        if symbol == "AIRLIQ":
            raise TickerNotFoundError(symbol)
        return market.History(symbol, None, "EUR", scale, "1d", [], None)

    monkeypatch.setattr(market, "history", fake_history)
    monkeypatch.setattr(
        classification,
        "quotes",
        lambda isins, prefer=None: {"FR0000120073": classification.Quote("AI.PA", "EUR")},
    )

    assert quotes_router._history("AIRLIQ", "1y", "FR0000120073").symbol == "AI.PA"
    assert asked == ["AIRLIQ", "AI.PA"]
    with pytest.raises(TickerNotFoundError):
        quotes_router._history("AIRLIQ", "1y", None)
