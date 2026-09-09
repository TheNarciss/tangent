"""Shiller (Yale) — S&P 500, inflation and long rates, monthly since 1871.

The `ie_data` workbook behind *Irrational Exuberance*. It is the only source
that reaches 1973-74 and 1987, the two crises our stress tests had to drop.

Its header spans four lines, so pandas cannot name the columns: we read them
by position, and `expect` in data_sources.yaml checks that the four header
lines at that position still say what we think. If Shiller reorders the sheet,
the read fails loudly instead of returning the wrong column.

Dates are floats — 1871.01 is January 1871, 1871.1 is October.
"""

import io
import logging

import pandas as pd

from ..errors import DataSourceError
from . import http
from .config import config

logger = logging.getLogger(__name__)


def columns() -> list[str]:
    """Column keys available in data_sources.yaml."""
    return list(config().shiller.columns)


def series(name: str) -> pd.Series:
    """One monthly Shiller column, indexed by month."""
    cfg = config().shiller
    column = cfg.columns.get(name)
    if not column:
        raise DataSourceError(f"Colonne inconnue dans data_sources.yaml: {name}")

    sheet = _sheet()
    _check_header(sheet, column.position, column.expect, name)

    body = sheet.iloc[cfg.first_data_row :]
    periods = _periods(body.iloc[:, 0])
    values = pd.to_numeric(body.iloc[:, column.position], errors="coerce")

    out = pd.Series(values.to_numpy(), index=periods).dropna()
    out = out[out.index.notna()]
    if out.empty:
        raise DataSourceError(f"Aucune observation exploitable pour {name}.")
    out.name = name
    return out.sort_index()


def window_return(name: str, start: str, end: str) -> float:
    """Return of a level series between two months, inclusive. Months are 'YYYY-MM'."""
    levels = series(name).loc[start:end]
    if len(levels) < 2:
        raise DataSourceError(f"Moins de deux observations {name} entre {start} et {end}.")
    return float(levels.iloc[-1] / levels.iloc[0] - 1.0)


def _periods(raw: pd.Series) -> pd.DatetimeIndex:
    """'1871.01' → janvier 1871, '1871.1' → octobre 1871."""
    numbers = pd.to_numeric(raw, errors="coerce")
    years = numbers.astype("Float64").astype(float) // 1
    months = ((numbers - years) * 100).round()
    stamps = [
        pd.Timestamp(year=int(y), month=int(m), day=1)
        if pd.notna(y) and pd.notna(m) and 1 <= m <= 12
        else pd.NaT
        for y, m in zip(years, months, strict=True)
    ]
    return pd.DatetimeIndex(stamps)


def _check_header(sheet: pd.DataFrame, position: int, expect: str, name: str) -> None:
    cfg = config().shiller
    if position >= sheet.shape[1]:
        raise DataSourceError(f"Colonne {position} absente du classeur Shiller ({name}).")

    parts = [
        str(sheet.iat[row, position]).strip()
        for row in cfg.label_rows
        if row < sheet.shape[0] and pd.notna(sheet.iat[row, position])
    ]
    header = " ".join(p for p in parts if p and p.lower() != "nan")
    if expect.casefold() not in header.casefold():
        raise DataSourceError(
            f"En-tête Shiller inattendu en colonne {position} pour {name} : "
            f"« {header} » ne contient pas « {expect} ». Le classeur a changé."
        )


def _sheet() -> pd.DataFrame:
    cfg = config().shiller
    workbook = http.get_bytes(cfg.url, ttl_hours=config().cache_hours.factors)
    try:
        return pd.read_excel(io.BytesIO(workbook), sheet_name=cfg.sheet, header=None, engine="xlrd")
    except Exception as exc:
        raise DataSourceError(f"Classeur Shiller illisible: {exc}") from exc
