"""Market data source. Wraps yfinance with a process-local TTL cache."""
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

_CACHE: dict[tuple[str, str], tuple[datetime, pd.DataFrame]] = {}
_TTL = timedelta(hours=1)


def fetch_prices(tickers: list[str], period: str = "5y") -> pd.DataFrame:
    """Adjusted close prices; index=date, columns=tickers."""
    key = (",".join(sorted(tickers)), period)
    cached = _CACHE.get(key)
    if cached and datetime.now() - cached[0] < _TTL:
        return cached[1].copy()

    data = yf.download(tickers, period=period, auto_adjust=True, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        prices = data[["Close"]].rename(columns={"Close": tickers[0]})
    prices = prices.dropna(how="all")

    _CACHE[key] = (datetime.now(), prices)
    return prices.copy()
