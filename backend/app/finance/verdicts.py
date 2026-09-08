"""Verdicts — the method's conclusions, one per technique (ADR-023).

A verdict is a status, one sentence, an amount in euros per year and an
action (or none). The engine computes here; the simple screens show the
status and the sentence, the Méthode tab unfolds `details`, and the
briefing reads the same list. Thresholds live in `config/verdicts.yaml`.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from ..db.models import Profile
from ..errors import ConfigurationError, UnknownBrokerError
from ..models import Verdict, VerdictsResponse, Wealth
from . import fees

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "verdicts.yaml"


class FeesThresholds(BaseModel):
    green_max: float = Field(ge=0)
    amber_max: float = Field(ge=0)
    reference: float = Field(ge=0)
    min_coverage: float = Field(ge=0, le=1)


class VerdictsConfig(BaseModel):
    fees: FeesThresholds


def _load_config() -> VerdictsConfig:
    if not _PATH.exists():
        raise ConfigurationError(f"Fichier de config verdicts manquant: {_PATH}.")
    try:
        raw = yaml.safe_load(_PATH.read_text())
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"YAML invalide dans {_PATH.name}: {exc}") from exc
    try:
        return VerdictsConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigurationError(f"Schéma verdicts.yaml invalide: {exc}") from exc


_CONFIG: VerdictsConfig | None = None


def config() -> VerdictsConfig:
    """Lazy-load the thresholds; cached for the process lifetime."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = _load_config()
    return _CONFIG


def _eur(value: float) -> str:
    """1234.5 → « 1 235 € » (narrow no-break space as thousands separator)."""
    return f"{value:,.0f} €".replace(",", " ")


def _pct(fraction: float) -> str:
    """0.0092 → « 0,92 % »."""
    return f"{fraction * 100:.2f} %".replace(".", ",")


def fees_verdict(
    wealth: Wealth,
    broker_fees: fees.BrokerFees,
    monthly_contribution: float,
    thresholds: FeesThresholds | None = None,
) -> Verdict:
    """« Frais réels » : what the user's lines cost per year, all layers summed.

    Fund fees = Σ current_value × TER (TER entered by the user or resolved,
    per line). Broker fees = custody on the lines' value + fixed fee per line
    + courtage on twelve monthly contributions. Prices are already net of
    fund fees, so nothing here feeds the projection: this is a cost of
    holding, shown once a year in euros.
    """
    cfg = thresholds or config().fees

    lines: list[dict[str, Any]] = []
    uncovered: list[dict[str, Any]] = []
    for acc in wealth.investment_accounts:
        if not acc.positions:
            if acc.value > 0:
                uncovered.append(
                    {"name": acc.name, "account_type": acc.account_type, "value_eur": acc.value}
                )
            continue
        for p in acc.positions:
            if p.current_value <= 0:
                continue
            lines.append(
                {
                    "ticker": p.ticker,
                    "label": p.label,
                    "account": acc.name,
                    "value_eur": p.current_value,
                    "ter": p.ter,
                    "fund_fee_eur": p.current_value * p.ter if p.ter is not None else None,
                }
            )

    positions_total = sum(line["value_eur"] for line in lines)
    if positions_total <= 0:
        return Verdict(
            id="fees",
            title="Frais réels",
            status="unknown",
            headline=(
                "Aucune ligne de placement connue : connecte un PEA, un compte-titres "
                "ou une assurance vie pour mesurer ce que tes placements te coûtent."
            ),
            details={"uncovered_accounts": uncovered},
        )

    missing = [line for line in lines if line["ter"] is None]
    known_value = sum(line["value_eur"] for line in lines if line["ter"] is not None)
    coverage = known_value / positions_total
    fund_fees = sum(line["fund_fee_eur"] or 0.0 for line in lines)
    broker_eur = (
        broker_fees.fixed_per_line_eur * len(lines)
        + broker_fees.custody_pct * positions_total
        + broker_fees.courtage_pct * monthly_contribution * 12.0
    )
    total = fund_fees + broker_eur
    total_pct = total / positions_total
    reference_eur = cfg.reference * positions_total
    saving = max(0.0, total - reference_eur)

    details: dict[str, Any] = {
        "positions_total_eur": positions_total,
        "total_fees_eur": total,
        "total_fees_pct": total_pct,
        "fund_fees_eur": fund_fees,
        "broker_fees_eur": broker_eur,
        "broker_name": broker_fees.name,
        "monthly_contribution_eur": monthly_contribution,
        "reference_pct": cfg.reference,
        "reference_eur": reference_eur,
        "coverage": coverage,
        "lines": sorted(lines, key=lambda line: line["value_eur"], reverse=True),
        "missing_ter": [
            {"ticker": m["ticker"], "label": m["label"], "value_eur": m["value_eur"]}
            for m in missing
        ],
        "uncovered_accounts": uncovered,
        "thresholds": {"green_max": cfg.green_max, "amber_max": cfg.amber_max},
    }

    if coverage < cfg.min_coverage:
        n = len(missing)
        return Verdict(
            id="fees",
            title="Frais réels",
            status="unknown",
            headline=(
                f"Il manque les frais annuels (TER) de {n} ligne{'s' if n > 1 else ''}, "
                f"soit {_pct(1 - coverage)} de tes placements : impossible de mesurer "
                "ce qu'ils te coûtent."
            ),
            action="Renseigne le TER de ces lignes dans Comptes (ouvre le compte, puis la ligne).",
            details=details,
        )

    at_least = "au moins " if missing else ""
    base = f"Tes placements te coûtent {at_least}{_pct(total_pct)} par an, soit {_eur(total)}"
    complete = (
        f" Renseigne le TER manquant sur {len(missing)} ligne{'s' if len(missing) > 1 else ''} "
        "pour affiner."
        if missing
        else ""
    )

    if total_pct <= cfg.green_max:
        return Verdict(
            id="fees",
            title="Frais réels",
            status="green",
            headline=base + " : c'est bas, rien à changer.",
            impact_eur_per_year=0.0,
            action=complete.strip() or None,
            details=details,
        )
    if total_pct <= cfg.amber_max:
        return Verdict(
            id="fees",
            title="Frais réels",
            status="amber",
            headline=(
                base + f" : la même somme en PEA en ligne avec un ETF monde coûterait "
                f"{_eur(reference_eur)}."
            ),
            impact_eur_per_year=saving,
            action=(
                f"Compare ton courtier et tes fonds : {_eur(saving)} par an d'écart avec la "
                "référence." + complete
            ),
            details=details,
        )
    return Verdict(
        id="fees",
        title="Frais réels",
        status="red",
        headline=(
            base + f", soit {_eur(saving)} de plus par an qu'un PEA en ligne avec un ETF monde."
        ),
        impact_eur_per_year=saving,
        action=(
            "Change de courtier ou remplace les fonds les plus chers par un ETF indiciel : "
            f"c'est {_eur(saving)} par an à récupérer." + complete
        ),
        details=details,
    )


def compute_all(wealth: Wealth, profile: Profile) -> VerdictsResponse:
    """Every verdict the method can give on this patrimony, in display order."""
    try:
        _, broker_fees = fees.get(profile.default_broker)
    except UnknownBrokerError:
        logger.warning("verdicts: unknown broker %r, using default", profile.default_broker)
        _, broker_fees = fees.get(None)
    monthly = float(profile.monthly_dca or 0.0)
    verdicts = [fees_verdict(wealth, broker_fees, monthly)]
    logger.info("verdicts computed: %s", {v.id: v.status for v in verdicts})
    return VerdictsResponse(computed_at=datetime.now(tz=UTC), verdicts=verdicts)
