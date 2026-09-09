"""Observed macro values: the risk-free rate and inflation.

Both were constants. The risk-free rate was written three times — in
`analytics.RISK_FREE`, in `verdicts.yaml` under `goal.risk_free`, and in the
comment tying the two together — and inflation once more in `verdicts.yaml`.
Three copies of one number drift apart; none of them updated.

They now come from the sources of truth (ADR-024): the ECB policy rate, and
the French harmonised price index. Each has a fallback in `config/macro.yaml`
used when the source is unreachable, so no page ever fails on a macro read.

Inflation is averaged over several years on purpose: a twenty-year projection
must not swing on one month's print.
"""

import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml
from pydantic import BaseModel, Field

from ..data import ecb, fred
from ..errors import ConfigurationError, DataSourceError

logger = logging.getLogger(__name__)
_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "macro.yaml"

PERCENT = 100.0


class RiskFreeConfig(BaseModel):
    series: str
    fallback: float = Field(ge=0)


class InflationConfig(BaseModel):
    series: str
    years: int = Field(gt=0)
    fallback: float


class MacroConfig(BaseModel):
    risk_free: RiskFreeConfig
    inflation: InflationConfig


@lru_cache(maxsize=1)
def config() -> MacroConfig:
    if not _PATH.exists():
        raise ConfigurationError("macro.yaml introuvable.")
    try:
        raw = yaml.safe_load(_PATH.read_text()) or {}
        return MacroConfig.model_validate(raw)
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError(f"macro.yaml malformé: {exc}") from exc


def risk_free_rate() -> float:
    """Short risk-free rate as a fraction (0.024 = 2,4 %). ECB policy rate."""
    cfg = config().risk_free
    try:
        series = ecb.named(cfg.series, last_n=1)
        return float(series.iloc[-1]) / PERCENT
    except (DataSourceError, IndexError, ValueError):
        logger.warning("taux sans risque indisponible, repli sur %.3f", cfg.fallback)
        return cfg.fallback


def inflation() -> float:
    """Annualised inflation over the configured window, as a fraction."""
    cfg = config().inflation
    try:
        index = fred.named(cfg.series)
        return _annualized(index, cfg.years)
    except (DataSourceError, IndexError, KeyError, ValueError):
        logger.warning("inflation indisponible, repli sur %.3f", cfg.fallback)
        return cfg.fallback


def _annualized(index: pd.Series, years: int) -> float:
    """Compound annual change of a price index over `years`, ending on its last point.

    The start is looked up by date rather than by position: the series can miss
    a month, and an offset in rows would then span the wrong period.
    """
    last = index.index[-1]
    start = last - pd.DateOffset(years=years)
    if start not in index.index:
        raise ValueError(f"pas d'observation en {start.date()}")
    ratio = float(index.iloc[-1]) / float(index.loc[start])
    if ratio <= 0:
        raise ValueError("indice de prix non positif")
    return ratio ** (1.0 / years) - 1.0
