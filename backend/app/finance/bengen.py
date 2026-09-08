"""Taux de retrait soutenable — capital nécessaire pour un revenu mensuel à vie,
et projection inverse pour estimer le temps requis.

Bengen (1994) trouvait 4 % sur les États-Unis 1926-1992 ; sur l'histoire
française, 4 % échoue dans plus de la moitié des cohortes (Pfau 2010). Le taux
par défaut vient de `config/verdicts.yaml` (`retirement.withdrawal_rate`),
3,5 % pour un portefeuille monde vu d'Europe (étude §1.4).

Implémentation simplifiée : capital = revenu_annuel / taux_retrait.
"""

import logging
import math

from pydantic import BaseModel, Field

from . import verdicts as _verdicts

logger = logging.getLogger(__name__)


def default_withdrawal_rate() -> float:
    """The sustainable initial withdrawal rate, versioned in verdicts.yaml."""
    return _verdicts.config().retirement.withdrawal_rate


class BengenRequest(BaseModel):
    target_monthly_income: float = Field(ge=0, description="€/mois passifs visés")
    withdrawal_rate: float = Field(
        default_factory=default_withdrawal_rate,
        ge=0.001,
        le=0.10,
        description="Taux de retrait annuel soutenable (verdicts.yaml, 3,5 %)",
    )
    current_capital: float = Field(default=0, ge=0)
    monthly_dca: float = Field(default=0, ge=0)
    expected_return: float = Field(default=0.08, ge=0, le=0.30, description="μ annuel attendu")


class BengenResponse(BaseModel):
    target_monthly_income: float
    yearly_passive_income: float
    capital_needed: float
    years_to_reach: float | None  # None si inatteignable
    months_to_reach: int | None
    rationale: str


def compute(req: BengenRequest) -> BengenResponse:
    capital_needed = req.target_monthly_income * 12 / req.withdrawal_rate
    yearly_income = req.target_monthly_income * 12
    monthly_r = req.expected_return / 12
    years = _years_to_target(capital_needed, req.current_capital, req.monthly_dca, monthly_r)

    if years is None:
        rationale = (
            f"Pour générer {req.target_monthly_income:.0f} €/mois ({yearly_income:.0f} €/an) "
            f"au taux de retrait {req.withdrawal_rate * 100:.1f} %, il faudrait un capital de "
            f"{capital_needed:,.0f} €. Pas atteignable au rythme actuel — augmente le DCA ou μ."
        )
        months = None
    elif years == 0:
        rationale = (
            f"Déjà atteint : ton capital de {req.current_capital:,.0f} € génère déjà "
            f"{req.target_monthly_income:.0f} €/mois soutenables au taux {req.withdrawal_rate * 100:.1f} %."
        )
        months = 0
    else:
        months = round(years * 12)
        rationale = (
            f"Pour {req.target_monthly_income:.0f} €/mois passifs ({yearly_income:.0f} €/an) "
            f"au taux de retrait {req.withdrawal_rate * 100:.1f} %, il te faut {capital_needed:,.0f} €. "
            f"Avec capital actuel {req.current_capital:,.0f} € + DCA {req.monthly_dca:.0f} €/mois "
            f"@ μ {req.expected_return * 100:.1f} % : atteint en {years:.1f} ans."
        )

    logger.info(
        "bengen: target=%.0f€/mois → capital=%.0f€, years=%s",
        req.target_monthly_income,
        capital_needed,
        years,
    )
    return BengenResponse(
        target_monthly_income=req.target_monthly_income,
        yearly_passive_income=yearly_income,
        capital_needed=capital_needed,
        years_to_reach=years,
        months_to_reach=months,
        rationale=rationale,
    )


def _years_to_target(target: float, pv: float, dca: float, monthly_r: float) -> float | None:
    """Forme fermée du nombre d'années pour atteindre `target` partant de `pv`
    avec DCA `dca` par mois et taux mensuel `monthly_r`.

    Solve : target = pv·(1+r)^t + dca·((1+r)^t − 1)/r
            (1+r)^t = (target + dca/r) / (pv + dca/r)
            t = log(ratio) / log(1+r)

    Retourne None si inatteignable.
    """
    if pv >= target:
        return 0.0
    if monthly_r <= 0:
        if dca <= 0:
            return None
        return (target - pv) / dca / 12
    if dca <= 0:
        if pv <= 0:
            return None
        return math.log(target / pv) / math.log(1 + monthly_r) / 12
    A = dca / monthly_r
    ratio = (target + A) / (pv + A)
    if ratio <= 1:
        return 0.0
    return math.log(ratio) / math.log(1 + monthly_r) / 12
