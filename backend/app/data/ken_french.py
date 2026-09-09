"""Kenneth French Data Library — long monthly market returns per region.

This is the only free source we found that reaches back before 2009 without a
licence cap: monthly market returns in USD, dividends included, built on the
Bloomberg database, refreshed monthly. Developed / Europe / North America /
Japan start in 1990-07, Emerging in 1989-07.

The published factor is `Mkt-RF` (market minus risk-free), so the total return
of the region is `Mkt-RF + RF`. Both are percentages; we return fractions.

Each archive holds one CSV with two blocks: monthly rows keyed `YYYYMM`, then
annual rows keyed `YYYY`. Missing points are written `-99.99`.
"""

import io
import logging
import re
import zipfile

import pandas as pd

from ..errors import DataSourceError
from . import http
from .config import config

logger = logging.getLogger(__name__)

MISSING = -99.99
_MONTHLY = re.compile(r"^\s*(\d{6})\s*,")
_ANNUAL = re.compile(r"^\s*(\d{4})\s*,")


def regions() -> list[str]:
    """Region keys available in data_sources.yaml."""
    return list(config().ken_french.regions)


def monthly_returns(region: str) -> pd.Series:
    """Total monthly return of the region, as a fraction, indexed by month end."""
    return _returns(region, _MONTHLY, "%Y%m")


def annual_returns(region: str) -> pd.Series:
    """Total annual return of the region, as a fraction, indexed by year end."""
    return _returns(region, _ANNUAL, "%Y")


def window_return(region: str, start: str, end: str) -> float:
    """Compound total return between two months, inclusive. Months are 'YYYY-MM'."""
    monthly = monthly_returns(region)
    window = monthly.loc[start:end]
    if window.empty:
        raise DataSourceError(f"Aucune donnée {region} entre {start} et {end}.")
    return float((1.0 + window).prod() - 1.0)


def _returns(region: str, pattern: re.Pattern[str], date_format: str) -> pd.Series:
    text = _csv_text(region)
    periods: list[str] = []
    values: list[float] = []

    for line in text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        cells = [c.strip() for c in line.split(",")]
        if len(cells) < 3:
            continue
        try:
            market_excess = float(cells[1])
            risk_free = float(cells[-1])
        except ValueError:
            continue
        if MISSING in (market_excess, risk_free):
            continue
        periods.append(match.group(1))
        values.append((market_excess + risk_free) / 100.0)

    if not periods:
        raise DataSourceError(f"Aucune ligne exploitable dans l'archive {region}.")

    index = pd.to_datetime(periods, format=date_format)
    out = pd.Series(values, index=index).sort_index()
    out.name = region
    return out


def _csv_text(region: str) -> str:
    cfg = config()
    filename = cfg.ken_french.regions.get(region)
    if not filename:
        raise DataSourceError(f"Région inconnue dans data_sources.yaml: {region}")

    archive = http.get_bytes(
        f"{cfg.ken_french.base_url}/{filename}", ttl_hours=cfg.cache_hours.factors
    )
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            names = [n for n in bundle.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise DataSourceError(f"Archive {filename} sans CSV.")
            return bundle.read(names[0]).decode("utf-8", errors="replace")
    except zipfile.BadZipFile as exc:
        raise DataSourceError(f"Archive {filename} illisible: {exc}") from exc
