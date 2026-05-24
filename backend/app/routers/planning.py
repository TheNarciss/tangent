"""Planning routes — strategy (glide path) + bengen (4% rule)."""

from fastapi import APIRouter, Depends

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
