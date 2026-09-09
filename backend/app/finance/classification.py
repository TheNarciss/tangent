"""What an instrument actually is: a fund or a share, and on which index.

Two questions the app kept answering with statistics instead of facts:

- « Ces deux fonds font doublon » was decided by a correlation above 0.85.
  Two trackers of the same index are not correlated, they are *identical*, and
  the index is written in the instrument's official name.
- « Une seule ligne pèse 60 % » was raised for any line. A single world ETF at
  100 % is the textbook recommendation, not a concentration risk; a single
  share at 40 % is.

The official name comes from OpenFIGI when we have an ISIN, and from the
label the bank returned otherwise. Matching rules live in
`config/asset_classes.yaml`.

An instrument we cannot recognise stays `unknown`. That is deliberate: the
previous default filed everything under world equities, which produced wrong
figures for any portfolio but the first user's.
"""

import logging
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ..data import openfigi
from ..errors import ConfigurationError, DataSourceError

logger = logging.getLogger(__name__)
_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "asset_classes.yaml"

FUND = "fund"
STOCK = "stock"
UNKNOWN_KIND = "unknown"


class Rule(BaseModel):
    asset_class: str = Field(alias="class")
    index: str
    broad: bool = False
    any: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class AssetClassesConfig(BaseModel):
    unknown_class: str = "unknown"
    instrument_kinds: dict[str, list[str]] = Field(default_factory=dict)
    rules: list[Rule] = Field(default_factory=list)
    history_regions: dict[str, str] = Field(default_factory=dict)


@dataclass(frozen=True)
class Classification:
    """What we know about one instrument, and where it came from."""

    asset_class: str
    index_label: str | None
    kind: str
    source: str  # 'openfigi' | 'label' | 'none'
    official_name: str | None = None
    broad: bool = False

    @property
    def is_known(self) -> bool:
        return self.asset_class != config().unknown_class

    @property
    def is_diversified(self) -> bool:
        """Spreads the risk widely: a fund, and on a broad index rather than one segment."""
        return self.kind == FUND and self.broad


@lru_cache(maxsize=1)
def config() -> AssetClassesConfig:
    if not _PATH.exists():
        raise ConfigurationError("asset_classes.yaml introuvable.")
    try:
        raw = yaml.safe_load(_PATH.read_text()) or {}
        return AssetClassesConfig.model_validate(raw)
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError(f"asset_classes.yaml malformé: {exc}") from exc


def unknown() -> Classification:
    return Classification(config().unknown_class, None, UNKNOWN_KIND, "none")


def history_region(asset_class: str) -> str | None:
    """Ken French region carrying a long history for this class, if there is one."""
    return config().history_regions.get(asset_class)


def classify(label: str | None, *, isin: str | None = None) -> Classification:
    """Classify one instrument. Falls back to the bank's label without the ISIN."""
    return classify_many([(label, isin)])[0]


def classify_many(instruments: list[tuple[str | None, str | None]]) -> list[Classification]:
    """Classify a batch of `(label, isin)` pairs with a single OpenFIGI call."""
    if not instruments:
        return []

    records = _reference_data([isin for _, isin in instruments if isin])
    out: list[Classification] = []
    for label, isin in instruments:
        record = records.get((isin or "").strip().upper())
        official = _official_name(record)
        kind = _kind(record)

        # Try both names and keep whichever one we recognise. The official name
        # is usually the better one, but not always: Amundi's Nasdaq tracker is
        # registered as « NASDQ-100 », a typo the bank's own label does not have.
        for name, source in ((official, "openfigi"), (label, "label")):
            if not name:
                continue
            found = _from_name(name, kind, source)
            if found.is_known:
                out.append(found)
                break
        else:
            fallback = official or label
            if fallback:
                logger.info("instrument non reconnu: %s", fallback)
                out.append(
                    Classification(
                        config().unknown_class,
                        None,
                        kind,
                        "openfigi" if official else "label",
                        fallback,
                    )
                )
            else:
                out.append(unknown())
    return out


def _from_name(name: str | None, kind: str, source: str) -> Classification:
    cfg = config()
    if not name:
        return unknown()

    haystack = _normalize(name)
    for rule in cfg.rules:
        if any(_normalize(pattern) in haystack for pattern in rule.any):
            return Classification(rule.asset_class, rule.index, kind, source, name, rule.broad)

    return Classification(cfg.unknown_class, None, kind, source, name)


def _reference_data(isins: list[str]) -> dict[str, dict]:
    """ISIN → best OpenFIGI record. Degrades to {} rather than breaking a page."""
    if not isins:
        return {}
    try:
        mapped = openfigi.map_isins(isins)
    except DataSourceError:
        logger.warning("OpenFIGI indisponible, repli sur les libellés de la banque")
        return {}
    return {isin: records[0] for isin, records in mapped.items() if records}


def _official_name(record: dict | None) -> str | None:
    return str(record.get("name")) if record and record.get("name") else None


def _kind(record: dict | None) -> str:
    if not record:
        return UNKNOWN_KIND
    declared = _normalize(str(record.get("securityType2") or ""))
    for kind, labels in config().instrument_kinds.items():
        if any(_normalize(label) == declared for label in labels):
            return kind
    return UNKNOWN_KIND


def _normalize(text: str) -> str:
    """Lowercase, accent-free, single-spaced — so 'Émergents' matches 'emergents'."""
    stripped = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in stripped if not unicodedata.combining(c))
    return " ".join(without_accents.lower().split())
