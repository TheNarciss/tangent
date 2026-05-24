"""Glide path — dérive un budget de risque recommandé selon âge + horizon.

Combine deux règles classiques :
- Bogle : « % actions max ≈ (rule_base − âge) » → traduit en σ_max via multiplicateur
- Horizon caps : court horizon = σ plafonnée plus bas (CFA Institute)

Le μ_target est dérivé du σ_max par une approximation linéaire de la frontière efficiente
classes d'actifs (r_f → actions monde long-terme).
"""

from typing import Literal

from pydantic import BaseModel, Field

GlideRule = Literal["100_age", "120_age", "custom"]
RiskLevel = Literal["prudent", "equilibre", "dynamique", "tres_dynamique"]

RISK_FREE_DEFAULT = 0.025
WORLD_RETURN_DEFAULT = 0.07
WORLD_VOL_REF = 0.20

# Plafonds horizon (CFA Institute) — durée → σ_max acceptable
_HORIZON_CAPS: list[tuple[int, int, float]] = [
    (0, 1, 0.02),  # < 1 an : quasi-livret
    (1, 3, 0.08),  # 1-3 ans : obligations courtes
    (3, 7, 0.12),  # 3-7 ans : mix équilibré
    (7, 15, 0.18),  # 7-15 ans : actions dominantes
    (15, 200, 0.25),  # > 15 ans : 100 % actions OK
]


class GlidePathResult(BaseModel):
    risk_level: RiskLevel
    max_volatility: float = Field(description="σ_max recommandée, fraction (e.g. 0.156)")
    target_return: float = Field(description="μ cible dérivé, fraction (e.g. 0.073)")
    drawdown_estimate: float = Field(
        description="Drawdown pire année estimé, fraction négative (= −2σ)"
    )
    rationale: str = Field(description="Phrase d'explication pour l'UI")


def compute(
    age: int,
    horizon_years: int,
    rule: GlideRule = "120_age",
    custom_multiplier: float = 0.20,
    risk_free: float = RISK_FREE_DEFAULT,
    world_return: float = WORLD_RETURN_DEFAULT,
) -> GlidePathResult:
    # 1. Part actions max selon règle d'âge
    base = 100 if rule == "100_age" else 120
    pct_equity = max(0.0, min(1.0, (base - age) / 100))
    sigma_from_age = pct_equity * (custom_multiplier if rule == "custom" else WORLD_VOL_REF)

    # 2. Plafond horizon
    sigma_cap = next((cap for lo, hi, cap in _HORIZON_CAPS if lo <= horizon_years < hi), 0.25)
    sigma_max = min(sigma_from_age, sigma_cap)

    # 3. μ cible via mapping linéaire frontière : σ=0 → r_f, σ=WORLD_VOL_REF → world_return
    target_return = risk_free + (sigma_max / WORLD_VOL_REF) * (world_return - risk_free)

    # 4. Drawdown attendu (loi normale, 97,5 %)
    drawdown_estimate = -2.0 * sigma_max

    # 5. Label sémantique
    if sigma_max < 0.06:
        risk_level: RiskLevel = "prudent"
    elif sigma_max < 0.13:
        risk_level = "equilibre"
    elif sigma_max < 0.20:
        risk_level = "dynamique"
    else:
        risk_level = "tres_dynamique"

    rationale = (
        f"À {age} ans avec un horizon de {horizon_years} ans, profil {risk_level.replace('_', ' ')} : "
        f"σ ≤ {sigma_max * 100:.1f} %, rendement cible {target_return * 100:.1f} %, "
        f"drawdown attendu pire année ≈ {drawdown_estimate * 100:.0f} %."
    )

    return GlidePathResult(
        risk_level=risk_level,
        max_volatility=sigma_max,
        target_return=target_return,
        drawdown_estimate=drawdown_estimate,
        rationale=rationale,
    )
