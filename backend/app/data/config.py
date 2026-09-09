"""Loads `config/data_sources.yaml`.

Same pattern as `finance/cma.py`: one cached read, a Pydantic model, and a
`ConfigurationError` if the file is malformed. Endpoints and series ids live
in the YAML so that adding a series never means touching Python.
"""

import logging
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ..errors import ConfigurationError

logger = logging.getLogger(__name__)
_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "data_sources.yaml"


class CacheHours(BaseModel):
    macro: float = 12.0
    factors: float = 24.0
    reference: float = 168.0


class FredConfig(BaseModel):
    base_url: str
    series: dict[str, str] = Field(default_factory=dict)


class EcbConfig(BaseModel):
    base_url: str
    series: dict[str, str] = Field(default_factory=dict)


class HicpConfig(BaseModel):
    dataset: str
    geo: str
    coicop: str
    unit: str


class EurostatConfig(BaseModel):
    base_url: str
    hicp: HicpConfig


class KenFrenchConfig(BaseModel):
    base_url: str
    regions: dict[str, str] = Field(default_factory=dict)


class DamodaranConfig(BaseModel):
    url: str
    sheet: str
    header_row: int = Field(ge=0)
    columns: dict[str, str] = Field(default_factory=dict)


class ShillerColumn(BaseModel):
    position: int = Field(ge=0)
    expect: str


class ShillerConfig(BaseModel):
    url: str
    sheet: str
    first_data_row: int = Field(ge=0)
    label_rows: list[int] = Field(default_factory=list)
    columns: dict[str, ShillerColumn] = Field(default_factory=dict)


class LbmaConfig(BaseModel):
    base_url: str
    series: dict[str, str] = Field(default_factory=dict)


class OpenFigiConfig(BaseModel):
    base_url: str
    max_isins_per_request: int = Field(default=10, gt=0)


class DataSourcesConfig(BaseModel):
    http_timeout_seconds: float = Field(default=20.0, gt=0)
    user_agent: str = "tangent/1.0"
    cache_hours: CacheHours = Field(default_factory=CacheHours)
    fred: FredConfig
    ecb: EcbConfig
    eurostat: EurostatConfig
    ken_french: KenFrenchConfig
    damodaran: DamodaranConfig
    shiller: ShillerConfig
    lbma: LbmaConfig
    openfigi: OpenFigiConfig


@lru_cache(maxsize=1)
def config() -> DataSourcesConfig:
    if not _PATH.exists():
        raise ConfigurationError("data_sources.yaml introuvable.")
    try:
        raw = yaml.safe_load(_PATH.read_text()) or {}
        return DataSourcesConfig.model_validate(raw)
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError(f"data_sources.yaml malformé: {exc}") from exc
