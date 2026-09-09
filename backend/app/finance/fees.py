"""Broker fee configuration: load `config/brokers.yaml` and expose typed access.

Fee model applied per month inside the projection:

    fee_t = fixed_per_line_eur × n_lines / 12
          + custody_pct × portfolio_value_t / 12
          + courtage_pct × monthly_contribution

Loaded once at import time; reload by restarting the process (config rarely
changes). Schema is enforced by Pydantic so malformed YAML fails fast.
"""

import logging
from collections.abc import Callable
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ..errors import ConfigurationError, UnknownBrokerError

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "brokers.yaml"


class BrokerFees(BaseModel):
    name: str
    fixed_per_line_eur: float = Field(ge=0)
    custody_pct: float = Field(ge=0)
    # Retrocessions the bank receives from fund managers: paid out of the fund's
    # TER, never charged to the client. Kept as information, not a cost.
    rebates_pct: float = Field(ge=0, default=0.0)
    courtage_pct: float = Field(ge=0)
    # True for the neutral entry used when we do not know the user's broker.
    # Its zeros are an absence of information, not a free broker: consumers
    # must say so rather than display a total that looks complete.
    placeholder: bool = False


class BrokerConfig(BaseModel):
    default_broker: str
    institution_to_broker: dict[str, str] = {}
    brokers: dict[str, BrokerFees]


def _load_config() -> BrokerConfig:
    if not _PATH.exists():
        raise ConfigurationError(f"Fichier de config brokers manquant: {_PATH}.")
    try:
        raw = yaml.safe_load(_PATH.read_text())
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"YAML invalide dans {_PATH.name}: {exc}") from exc
    try:
        cfg = BrokerConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigurationError(f"Schéma brokers.yaml invalide: {exc}") from exc
    if cfg.default_broker not in cfg.brokers:
        raise ConfigurationError(
            f"default_broker={cfg.default_broker!r} absent de la liste {list(cfg.brokers)}.",
        )
    logger.info(
        "loaded %d brokers from %s (default: %s)", len(cfg.brokers), _PATH.name, cfg.default_broker
    )
    return cfg


_CONFIG: BrokerConfig | None = None


def config() -> BrokerConfig:
    """Lazy-load the broker config; cached for the process lifetime."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = _load_config()
    return _CONFIG


def get(broker_id: str | None = None) -> tuple[str, BrokerFees]:
    """Return (broker_id, fees). Falls back to default if `broker_id` is None.

    Raises:
        UnknownBrokerError: if `broker_id` is not in the loaded config.
    """
    c = config()
    bid = broker_id or c.default_broker
    if bid not in c.brokers:
        raise UnknownBrokerError(
            f"Broker inconnu: {bid!r}. Valeurs: {list(c.brokers)}.",
        )
    return bid, c.brokers[bid]


def monthly_fee_fn(
    fees: BrokerFees, n_lines: int, monthly_contribution: float
) -> Callable[[float], float]:
    """Build a `value → monthly_fee_eur` function specialised on a config + state.

    Used inside the Monte-Carlo / deterministic simulation loops so each path
    pays its own fees based on its own current value.
    """
    fixed_monthly = fees.fixed_per_line_eur * n_lines / 12.0
    prop = fees.custody_pct / 12.0
    courtage_monthly = fees.courtage_pct * monthly_contribution

    def fee_of(value: float) -> float:
        return fixed_monthly + prop * value + courtage_monthly

    return fee_of


def autodetect_broker(institution_name: str | None) -> str | None:
    """Match a Powens institution_name against the YAML mapping (case-insensitive).

    Returns the broker_id if a substring of the institution matches a key
    in `institution_to_broker`. Returns None on no match.
    """
    if not institution_name:
        return None
    mapping = config().institution_to_broker
    needle = institution_name.lower()
    for institution, broker_id in mapping.items():
        if institution.lower() in needle:
            return broker_id
    return None
