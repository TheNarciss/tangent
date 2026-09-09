"""Planning routes — the app's one sustainable withdrawal rate."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..auth import User, current_active_user
from ..finance import withdrawal

router = APIRouter(tags=["planning"])


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
    rate = withdrawal.default_withdrawal_rate()
    return WithdrawalRateResponse(
        withdrawal_rate=rate,
        note=(
            f"{rate * 100:.1f} % par an : taux de retrait initial soutenable pour un portefeuille "
            "monde vu d'Europe (Pfau, Early Retirement Now). La règle américaine des 4 % échoue "
            "dans plus de la moitié de l'histoire française."
        ),
    )
