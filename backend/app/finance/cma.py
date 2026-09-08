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
_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "cma.yaml"

# Par défaut, on tire μ à 70 % vers les CMAs long-terme.
# 0 = pure historique 5y (gonflé) ; 1 = pure CMA (prudent forward-looking).
SHRINKAGE_DEFAULT = 0.70


class CMAConfig(BaseModel):
    tickers: dict[str, float] = Field(default_factory=dict)
    # Kept for backward-compatible parsing of cma.yaml; no longer applied.
    default_return: float | None = None


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


def get_return(ticker: str, overrides: dict[str, float] | None = None) -> float | None:
    """μ forward-looking. Overrides > config > None (no CMA known for this ticker)."""
    if overrides and ticker in overrides:
        return overrides[ticker]
    return config().tickers.get(ticker)


def unmapped_tickers(tickers: list[str], overrides: dict[str, float] | None = None) -> list[str]:
    """Tickers with no CMA (neither in cma.yaml nor in the expert overrides)."""
    return [t for t in tickers if get_return(t, overrides) is None]


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

    A ticker with no CMA keeps its historical μ untouched: assigning it a
    generic equity-like return (the old ``default_return``) paired with its own
    small σ made money-market or bond funds look like the best asset on earth.
    Callers surface such tickers via :func:`unmapped_tickers`.
    """
    s = SHRINKAGE_DEFAULT if shrinkage is None else max(0.0, min(1.0, shrinkage))
    out = np.array(historical_mu, dtype=float).copy()
    for i, t in enumerate(tickers):
        cma_mu = get_return(t, overrides)
        if cma_mu is not None:
            out[i] = (1 - s) * historical_mu[i] + s * cma_mu
        else:
            logger.warning("cma: no forward-looking μ for %s, historical μ kept", t)
    return out
