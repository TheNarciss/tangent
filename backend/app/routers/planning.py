"""Planning routes — strategy (glide path), withdrawal rate, bengen (capital for an income)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..auth import User, current_active_user
from ..finance import bengen, glide_path
from ..models import StrategyRequest

router = APIRouter(tags=["planning"])


@router.post("/strategy", response_model=glide_path.GlidePathResult)
async def read_strategy(
    req: StrategyRequest,
    user: User = Depends(current_active_user),
) -> glide_path.GlidePathResult:
    """Computes the recommended strategy for this profile via glide path.

    Stateless computation — no DB access needed, just runs the formula.
    Still gated by auth so anonymous traffic can't probe it.
    """
    return glide_path.compute(
        age=req.age,
        horizon_years=req.horizon_years,
        rule=req.rule,  # type: ignore[arg-type]
        custom_multiplier=req.custom_multiplier or 0.20,
    )


@router.post("/bengen", response_model=bengen.BengenResponse)
async def read_bengen(
    req: bengen.BengenRequest,
    user: User = Depends(current_active_user),
) -> bengen.BengenResponse:
    """Capital required to generate a sustainable monthly income + reverse projection."""
    return bengen.compute(req)


class WithdrawalRateResponse(BaseModel):
    withdrawal_rate: float  # fraction, e.g. 0.035
    note: str


@router.get("/withdrawal-rate", response_model=WithdrawalRateResponse)
async def read_withdrawal_rate(
    user: User = Depends(current_active_user),
) -> WithdrawalRateResponse:
    """The one sustainable withdrawal rate of the app (config/verdicts.yaml).

    Read by the Projection page to turn « un revenu mensuel à vie » into a
    capital goal, so the frontend carries no copy of the value.
    """
    rate = bengen.default_withdrawal_rate()
    return WithdrawalRateResponse(
        withdrawal_rate=rate,
        note=(
            f"{rate * 100:.1f} % par an : taux de retrait initial soutenable pour un portefeuille "
            "monde vu d'Europe (Pfau, Early Retirement Now). La règle américaine des 4 % échoue "
            "dans plus de la moitié de l'histoire française."
        ),
    )
