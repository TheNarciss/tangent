"""Market data source. Wraps yfinance with a TTL cache, in memory and on disk.

Daily closes do not move during the day, and Yahoo is the slowest source the
app has (seconds per batch, minutes when it throttles), so a batch fetched
once serves twelve hours. The on-disk copy under `data/prices/` survives a
restart: a deploy no longer turns every screen cold at once.

Failures are reported via the application's exception hierarchy:
- network/upstream issues → `MarketDataError`
- valid request but unknown/empty tickers → `TickerNotFoundError`
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from ..errors import MarketDataError, TickerNotFoundError

logger = logging.getLogger(__name__)

_CACHE: dict[tuple[str, str], tuple[datetime, pd.DataFrame]] = {}
_TTL = timedelta(hours=12)
_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "prices"


def fetch_prices(
    tickers: list[str], period: str = "5y", *, drop_missing: bool = False
) -> pd.DataFrame:
    """Adjusted close prices; index=date, columns=tickers.

    `drop_missing=True` keeps the batch alive when Yahoo does not know one of
    a hundred tickers: the unknown ones are logged and left out instead of
    failing the whole download. The strict default is what the portfolio
    screens want — a missing line there is an error to show.

    Raises:
        TickerNotFoundError: if every ticker is missing or empty.
        MarketDataError: on network/upstream failures.
    """
    if not tickers:
        raise TickerNotFoundError("Aucun ticker fourni.")

    key = (",".join(sorted(tickers)), period)
    cached = _CACHE.get(key) or _read_disk(key)
    if cached and datetime.now() - cached[0] < _TTL:
        logger.debug("cache hit: %s", key)
        _CACHE[key] = cached
        return cached[1].copy()

    try:
        data = yf.download(tickers, period=period, auto_adjust=True, progress=False)
    except Exception as exc:
        logger.exception("yfinance failure for %s", tickers)
        raise MarketDataError(f"Échec de la récupération Yahoo Finance: {exc}") from exc

    if data is None or data.empty:
        raise TickerNotFoundError(f"Yahoo Finance n'a retourné aucune donnée pour: {tickers}")

    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        prices = data[["Close"]].rename(columns={"Close": tickers[0]})
    prices = prices.dropna(how="all")

    # Per-ticker check: drop entirely-NaN columns and flag them
    missing = [t for t in tickers if t not in prices.columns or prices[t].dropna().empty]
    if missing and drop_missing and len(missing) < len(tickers):
        logger.warning("tickers sans historique Yahoo, ignorés: %s", missing)
        prices = prices.drop(columns=[t for t in missing if t in prices.columns])
        missing = []
    if missing:
        raise TickerNotFoundError(
            f"Tickers introuvables ou sans historique exploitable: {missing}. "
            "Vérifie l'orthographe Yahoo Finance (ex: CW8.PA, PUST.PA, ETZ.PA)."
        )

    if len(prices) < 2:
        raise TickerNotFoundError(
            f"Historique trop court ({len(prices)} observation) pour: {tickers}."
        )

    _CACHE[key] = (datetime.now(), prices)
    _write_disk(key, prices)
    logger.info("fetched %s (%d days, %d tickers)", tickers, len(prices), len(prices.columns))
    return prices.copy()


def _file(key: tuple[str, str]) -> Path:
    return _DIR / f"{hashlib.sha256(f'{key[0]}|{key[1]}'.encode()).hexdigest()}.csv"


def _read_disk(key: tuple[str, str]) -> tuple[datetime, pd.DataFrame] | None:
    path = _file(key)
    try:
        if not path.exists():
            return None
        # CSV, not pickle: a file on disk must never be able to run code.
        frame = pd.read_csv(path, index_col=0, parse_dates=True)
        return (datetime.fromtimestamp(path.stat().st_mtime), frame)
    except Exception:  # a corrupt or half-written file is a miss, never an error
        logger.warning("cache disque illisible, ignoré: %s", path)
        return None


def _write_disk(key: tuple[str, str], prices: pd.DataFrame) -> None:
    """Best effort: a read-only data directory costs a warning, not a request."""
    try:
        _DIR.mkdir(parents=True, exist_ok=True)
        tmp = _file(key).with_suffix(".tmp")
        prices.to_csv(tmp)
        tmp.replace(_file(key))
        for old in _DIR.glob("*.csv"):
            if datetime.now() - datetime.fromtimestamp(old.stat().st_mtime) > 2 * _TTL:
                old.unlink(missing_ok=True)
    except Exception:
        logger.warning("cache disque non inscriptible: %s", _DIR)


# ─── One line's own quote: its history at a chosen scale, and a name search ──
#
# What the price sheet and the « Cours » tab read. Unlike `fetch_prices`, a
# call here is about one symbol at one scale, and the intraday scales go
# stale in minutes rather than hours, so they get their own short cache.


@dataclass(frozen=True)
class Scale:
    """One button of the price sheet: the Yahoo period and bar size behind it."""

    period: str
    interval: str
    ttl: timedelta


SCALES: dict[str, Scale] = {
    "1d": Scale("1d", "5m", timedelta(minutes=5)),
    "1w": Scale("5d", "15m", timedelta(minutes=5)),
    "1m": Scale("1mo", "1h", timedelta(minutes=15)),
    "6m": Scale("6mo", "1d", timedelta(hours=1)),
    "1y": Scale("1y", "1d", timedelta(hours=1)),
    "5y": Scale("5y", "1wk", timedelta(hours=12)),
    "max": Scale("max", "1mo", timedelta(hours=12)),
}


@dataclass(frozen=True)
class Point:
    t: str  # ISO-8601 with the exchange's offset
    close: float


@dataclass(frozen=True)
class History:
    symbol: str
    name: str | None
    currency: str
    scale: str
    interval: str
    points: list[Point]
    previous_close: float | None  # the close before the window, for the 1-day change


@dataclass(frozen=True)
class Match:
    symbol: str
    name: str
    exchange: str
    kind: str  # equity | etf | index


_HISTORY: dict[tuple[str, str], tuple[datetime, History]] = {}
_SEARCH: dict[str, tuple[datetime, list[Match]]] = {}
_SEARCH_TTL = timedelta(hours=1)
_KINDS = {"EQUITY": "equity", "ETF": "etf", "INDEX": "index"}


def history(symbol: str, scale: str) -> History:
    """One symbol's closes at one scale, from Yahoo, cached per scale.

    Raises:
        TickerNotFoundError: when the scale is unknown or Yahoo has no bars.
        MarketDataError: when Yahoo fails.
    """
    spec = SCALES.get(scale)
    if spec is None:
        raise TickerNotFoundError(f"Échelle inconnue: {scale}")
    key = (symbol, scale)
    cached = _HISTORY.get(key)
    if cached and datetime.now() - cached[0] < spec.ttl:
        return cached[1]

    try:
        ticker = yf.Ticker(symbol)
        bars = ticker.history(period=spec.period, interval=spec.interval, auto_adjust=True)
        meta = ticker.history_metadata or {}
    except Exception as exc:
        logger.exception("yfinance failure for %s", symbol)
        raise MarketDataError(f"Échec de la récupération Yahoo Finance: {exc}") from exc

    closes = (
        bars["Close"].dropna() if bars is not None and "Close" in bars else pd.Series(dtype=float)
    )
    if closes.empty:
        raise TickerNotFoundError(f"Yahoo Finance ne connaît pas {symbol}.")

    out = History(
        symbol=str(meta.get("symbol") or symbol),
        name=meta.get("longName") or meta.get("shortName") or None,
        currency=str(meta.get("currency") or ""),
        scale=scale,
        interval=spec.interval,
        points=[Point(t=ts.isoformat(), close=float(c)) for ts, c in closes.items()],
        previous_close=_number(meta.get("chartPreviousClose") or meta.get("previousClose")),
    )
    _HISTORY[key] = (datetime.now(), out)
    return out


def search(query: str, *, limit: int = 8) -> list[Match]:
    """Shares, funds and indices whose name or symbol matches, best first.

    Yahoo's own search box, so a user finds « air liquide » the same way they
    would on the site. Never raises: a failure is an empty list, which the
    screen shows as « rien trouvé ».
    """
    q = " ".join(query.split()).lower()
    if not q:
        return []
    cached = _SEARCH.get(q)
    if cached and datetime.now() - cached[0] < _SEARCH_TTL:
        return cached[1]
    try:
        quotes = yf.Search(q, max_results=limit * 2, news_count=0).quotes
    except Exception:
        logger.warning("recherche Yahoo en échec pour %r", q)
        return []
    out = parse_search(quotes, limit=limit)
    _SEARCH[q] = (datetime.now(), out)
    return out


def parse_search(quotes: list[dict], *, limit: int = 8) -> list[Match]:
    """Yahoo's raw matches → what the screen lists, listed instruments only."""
    out: list[Match] = []
    for q in quotes:
        kind = _KINDS.get(str(q.get("quoteType") or ""))
        symbol = str(q.get("symbol") or "").strip()
        name = str(q.get("longname") or q.get("shortname") or "").strip()
        if not kind or not symbol or not name:
            continue
        out.append(Match(symbol, name, str(q.get("exchDisp") or q.get("exchange") or ""), kind))
        if len(out) == limit:
            break
    return out


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None
