"""Market data source. Wraps yfinance with a process-local TTL cache.

Failures are reported via the application's exception hierarchy:
- network/upstream issues → `MarketDataError`
- valid request but unknown/empty tickers → `TickerNotFoundError`
"""
import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from ..errors import MarketDataError, TickerNotFoundError

logger = logging.getLogger(__name__)

_CACHE: dict[tuple[str, str], tuple[datetime, pd.DataFrame]] = {}
_TTL = timedelta(hours=1)


def fetch_prices(tickers: list[str], period: str = "5y") -> pd.DataFrame:
    """Adjusted close prices; index=date, columns=tickers.

    Raises:
        TickerNotFoundError: if every ticker is missing or empty.
        MarketDataError: on network/upstream failures.
    """
    if not tickers:
        raise TickerNotFoundError("Aucun ticker fourni.")

    key = (",".join(sorted(tickers)), period)
    cached = _CACHE.get(key)
    if cached and datetime.now() - cached[0] < _TTL:
        logger.debug("cache hit: %s", key)
        return cached[1].copy()

    try:
        data = yf.download(tickers, period=period, auto_adjust=True, progress=False)
    except Exception as exc:  # noqa: BLE001 — yfinance throws many types
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
    logger.info("fetched %s (%d days, %d tickers)", tickers, len(prices), len(prices.columns))
    return prices.copy()