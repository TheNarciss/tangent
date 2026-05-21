"""Capital Market Assumptions — forward-looking expected returns per ticker.

Source : moyennes long-terme (Dimson-Marsh-Staunton 100y, Vanguard CMAs, JP Morgan LTCMA).
Moins biaisé que les μ historiques 5y de yfinance qui sont gonflés par le bull-run post-COVID.
"""
import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml
from pydantic import BaseModel, Field

from ..errors import ConfigurationError

logger = logging.getLogger(__name__)
_PATH = Path(__file__).resolve().parent.parent / "config" / "cma.yaml"

# Par défaut, on tire μ à 70 % vers les CMAs long-terme.
# 0 = pure historique 5y (gonflé) ; 1 = pure CMA (prudent forward-looking).
SHRINKAGE_DEFAULT = 0.70


class CMAConfig(BaseModel):
    tickers: dict[str, float] = Field(default_factory=dict)
    default_return: float = 0.07


@lru_cache(maxsize=1)
def config() -> CMAConfig:
    if not _PATH.exists():
        logger.warning("cma.yaml missing, returning empty defaults")
        return CMAConfig()
    try:
        raw = yaml.safe_load(_PATH.read_text()) or {}
        return CMAConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigurationError(f"cma.yaml malformé: {exc}") from exc


def get_return(ticker: str, overrides: dict[str, float] | None = None) -> float:
    """μ forward-looking. Overrides > config > default."""
    if overrides and ticker in overrides:
        return overrides[ticker]
    cfg = config()
    return cfg.tickers.get(ticker, cfg.default_return)


def blended_mu(
    tickers: list[str],
    historical_mu: np.ndarray,
    shrinkage: float | None = None,
    overrides: dict[str, float] | None = None,
) -> np.ndarray:
    """Blend historical and CMA μ. shrinkage: 0 = pure historical, 1 = pure CMA.

    Default shrinkage = 0.70 (70 % CMA) car les μ historiques 5y sont en moyenne
    gonflés de +10 points sur la période post-2020. Tire l'optimisation vers des
    espérances réalistes long-terme.
    """
    s = SHRINKAGE_DEFAULT if shrinkage is None else max(0.0, min(1.0, shrinkage))
    cma_mu = np.array([get_return(t, overrides) for t in tickers])
    return (1 - s) * historical_mu + s * cma_mu