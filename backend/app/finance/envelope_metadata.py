"""Lookup envelope metadata (rate, ceiling, name) from envelopes.yaml.

The YAML catalog (loaded by finance/envelopes.py::config()) is the source of
truth for regulated savings products' characteristics. This module exposes
a type-safe lookup for Wealth construction.

If an envelope key is missing from the YAML, lookup returns None (Wealth can
still represent the envelope with metadata blank — better than crashing on
an unknown product).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..aggregator import AccountType
from .envelopes import config as envelopes_config

logger = logging.getLogger(__name__)


# Powens-side AccountType → envelopes.yaml key.
# Note: livret_a_jeune is age-gated (12-25). The default mapping resolves to
# livret_a; the eligibility module determines whether the user qualifies for
# livret_a_jeune.
_ACCOUNT_TYPE_TO_YAML_KEY: dict[AccountType, str] = {
    AccountType.LIVRET_A: "livret_a",
    AccountType.LIVRET_B: "livret_b",
    AccountType.LDDS: "ldds",
    AccountType.LEP: "lep",
    AccountType.PEL: "pel",
    AccountType.CEL: "cel",
    AccountType.CSL: "csl",
    AccountType.CAT: "cat",
}


@dataclass(frozen=True)
class EnvelopeMetadata:
    """Resolved metadata for an envelope (from YAML)."""

    display_name: str
    rate_pct: float | None
    ceiling_eur: float | None
    tax_status: str | None


def is_envelope_type(account_type: AccountType) -> bool:
    """True if this AccountType is a regulated savings envelope."""
    return account_type in _ACCOUNT_TYPE_TO_YAML_KEY


def get_envelope_yaml_key(account_type: AccountType) -> str | None:
    """Return the envelopes.yaml key for an AccountType, or None."""
    return _ACCOUNT_TYPE_TO_YAML_KEY.get(account_type)


def get_metadata(account_type: AccountType) -> EnvelopeMetadata | None:
    """Resolve envelope metadata from envelopes.yaml.

    Returns None if the AccountType doesn't correspond to a regulated envelope,
    or if the envelope key is absent from the YAML (logged at WARNING).
    """
    yaml_key = get_envelope_yaml_key(account_type)
    if yaml_key is None:
        return None

    spec = envelopes_config().envelopes.get(yaml_key)
    if spec is None:
        logger.warning(
            "Envelope key %r mapped from AccountType.%s but missing from envelopes.yaml — "
            "envelope will have null metadata",
            yaml_key,
            account_type.name,
        )
        return None

    return EnvelopeMetadata(
        display_name=spec.name,
        rate_pct=spec.rate_pct,
        ceiling_eur=spec.ceiling_eur,
        tax_status=spec.tax_status,
    )
