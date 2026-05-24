"""Catalogue des enveloppes réglementées + filtre d'éligibilité.

Charge `config/envelopes.yaml` une fois au démarrage et expose une fonction
`eligible(age, rfr, fiscal_shares)` qui retourne pour chaque enveloppe son
statut + la raison (éligible ou non, et pourquoi).

L'utilisateur garde une vue claire : on lui montre TOUTES les enveloppes,
avec celles non-éligibles grisées et la raison affichée — pédagogique.
"""

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ..errors import ConfigurationError

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "envelopes.yaml"


class EligibilityRules(BaseModel):
    age_min: int = 0
    age_max: int | None = None
    rfr_max_base: float | None = None  # plafond RFR pour 1 part
    rfr_max_per_half_share: float | None = None  # incrément par demi-part suppl.


class Envelope(BaseModel):
    name: str
    rate_pct: float = Field(ge=0)
    ceiling_eur: float | None = Field(default=None, ge=0)
    tax_status: str
    liquidity_days: int = Field(ge=0)
    eligibility: EligibilityRules


class EnvelopesConfig(BaseModel):
    envelopes: dict[str, Envelope]


_CONFIG: EnvelopesConfig | None = None


def _load() -> EnvelopesConfig:
    if not _PATH.exists():
        raise ConfigurationError(f"Fichier de config enveloppes manquant: {_PATH}.")
    try:
        raw = yaml.safe_load(_PATH.read_text())
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"YAML invalide dans {_PATH.name}: {exc}") from exc
    try:
        cfg = EnvelopesConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigurationError(f"Schéma envelopes.yaml invalide: {exc}") from exc
    logger.info("loaded %d envelopes from %s", len(cfg.envelopes), _PATH.name)
    return cfg


def config() -> EnvelopesConfig:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = _load()
    return _CONFIG


def _rfr_ceiling(rules: EligibilityRules, fiscal_shares: float) -> float | None:
    """Calcule le plafond RFR effectif pour un nombre de parts donné.

    Formule conventionnelle: base + per_half_share × (fiscal_shares × 2 − 2),
    soit `base` pour 1 part puis +per_half_share par demi-part supplémentaire.
    """
    if rules.rfr_max_base is None or rules.rfr_max_per_half_share is None:
        return None
    half_shares_extra = max(0.0, fiscal_shares * 2 - 2)
    return rules.rfr_max_base + rules.rfr_max_per_half_share * half_shares_extra


def check_eligibility(
    env: Envelope,
    age: int,
    rfr: float,
    fiscal_shares: float,
) -> tuple[bool, str]:
    """Retourne (eligible, note) pour une enveloppe + un profil."""
    rules = env.eligibility

    if age < rules.age_min:
        return False, f"Âge minimum {rules.age_min} ans (tu as {age})."
    if rules.age_max is not None and age > rules.age_max:
        return False, f"Réservé aux {rules.age_min}-{rules.age_max} ans (tu as {age})."

    ceiling = _rfr_ceiling(rules, fiscal_shares)
    if ceiling is not None:
        if rfr > ceiling:
            return (
                False,
                f"RFR {rfr:,.0f} € > plafond {ceiling:,.0f} € pour {fiscal_shares} part(s).",
            )
        return True, f"RFR {rfr:,.0f} € ≤ plafond {ceiling:,.0f} € pour {fiscal_shares} part(s)."

    return True, "Conditions d'éligibilité satisfaites."
