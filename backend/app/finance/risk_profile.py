"""Risk slider levels (« prudent ↔ dynamique ») loaded from config/risk_levels.yaml.

One level = the pair (target annual return, max annual volatility) the
optimizer's `from_strategy` objective and the LLM briefing read from the
profile. The YAML is the single source of truth; the frontend fetches the
list through GET /profile/risk-levels to label its slider.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from ..errors import ConfigurationError

_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "risk_levels.yaml"


class RiskLevel(BaseModel):
    level: int = Field(..., ge=1, le=5)
    label: str
    target_annual_return: float = Field(..., ge=0, le=2, description="fraction, 0.07 = 7 %/an")
    max_annual_volatility: float = Field(..., ge=0, le=1, description="fraction")


class _RiskLevelsConfig(BaseModel):
    levels: list[RiskLevel]


_CONFIG: list[RiskLevel] | None = None


def _load() -> list[RiskLevel]:
    try:
        raw = yaml.safe_load(_PATH.read_text())
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"risk_levels.yaml illisible: {exc}") from exc
    try:
        cfg = _RiskLevelsConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigurationError(f"Schéma risk_levels.yaml invalide: {exc}") from exc
    levels = sorted(cfg.levels, key=lambda lv: lv.level)
    if [lv.level for lv in levels] != list(range(1, len(levels) + 1)):
        raise ConfigurationError("risk_levels.yaml: les crans doivent être 1..N sans trou.")
    return levels


def levels() -> list[RiskLevel]:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = _load()
    return _CONFIG


def resolve(level: int) -> RiskLevel:
    """The constraints attached to a slider position (1 = prudent)."""
    for lv in levels():
        if lv.level == level:
            return lv
    raise ConfigurationError(f"Cran de risque inconnu: {level}")
