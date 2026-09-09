"""Damodaran (NYU Stern) — annual returns of the big US asset classes since 1928.

The only free, unbridled source we found for **bonds** over a long window:
S&P 500 with dividends, small caps, 3-month T-Bill, 10-year T-Bond, Baa
corporates, real estate. One row per year, values already expressed as
fractions. Updated once a year, in January.

Two limits to keep in mind before using a number from here: it is **annual**
(a crash inside a year is invisible) and it is **American, in dollars**.
"""

import io
import logging
import warnings

import pandas as pd

from ..errors import DataSourceError
from . import http
from .config import config

logger = logging.getLogger(__name__)

_YEAR = r"^\d{4}(\.0)?$"


def classes() -> list[str]:
    """Asset class keys available in data_sources.yaml."""
    return list(config().damodaran.columns)


def annual_returns(asset_class: str) -> pd.Series:
    """Annual total return of the class, as a fraction, indexed by year end."""
    cfg = config().damodaran
    label = cfg.columns.get(asset_class)
    if not label:
        raise DataSourceError(f"Classe inconnue dans data_sources.yaml: {asset_class}")

    frame = _sheet()
    column = _column(frame, label, asset_class)
    years = frame.iloc[:, 0].astype(str).str.strip()
    keep = years.str.match(_YEAR, na=False)

    values = pd.to_numeric(column[keep], errors="coerce")
    index = pd.to_datetime(years[keep].str.slice(0, 4), format="%Y")
    out = pd.Series(values.to_numpy(), index=index).dropna()
    if out.empty:
        raise DataSourceError(f"Aucune observation exploitable pour {asset_class}.")
    out.name = asset_class
    return out.sort_index()


def window_return(asset_class: str, first_year: int, last_year: int) -> float:
    """Compound return of the class over whole years, both ends included."""
    annual = annual_returns(asset_class)
    window = annual[(annual.index.year >= first_year) & (annual.index.year <= last_year)]
    if window.empty:
        raise DataSourceError(f"Aucune année {asset_class} entre {first_year} et {last_year}.")
    return float((1.0 + window).prod() - 1.0)


def _column(frame: pd.DataFrame, label: str, asset_class: str) -> pd.Series:
    wanted = label.strip().casefold()
    for name in frame.columns:
        if str(name).strip().casefold() == wanted:
            return frame[name]
    raise DataSourceError(
        f"Colonne « {label} » absente du classeur Damodaran (classe {asset_class}). "
        "Le fichier a probablement été réorganisé : vérifie data_sources.yaml."
    )


def _sheet() -> pd.DataFrame:
    cfg = config().damodaran
    workbook = http.get_bytes(cfg.url, ttl_hours=config().cache_hours.factors)
    try:
        with warnings.catch_warnings():
            # The workbook carries a header/footer openpyxl cannot parse; harmless.
            warnings.filterwarnings("ignore", message="Cannot parse header or footer")
            return pd.read_excel(
                io.BytesIO(workbook),
                sheet_name=cfg.sheet,
                header=cfg.header_row,
                engine="openpyxl",
            )
    except Exception as exc:
        raise DataSourceError(f"Classeur Damodaran illisible: {exc}") from exc
