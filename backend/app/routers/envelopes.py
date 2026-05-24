"""Envelopes + brokers — config-driven endpoints (no user data).

Still gated by auth so anonymous traffic can't probe config.
"""

from fastapi import APIRouter, Depends

from ..auth import User, current_active_user
from ..finance import envelopes, fees
from ..models import (
    BrokerInfo,
    BrokersResponse,
    EligibilityRequest,
    EligibleEnvelopesResponse,
    EnvelopeEligibility,
)

router = APIRouter(tags=["config"])


@router.get("/brokers", response_model=BrokersResponse)
async def read_brokers(user: User = Depends(current_active_user)) -> BrokersResponse:
    """List of brokers available in config/brokers.yaml, with the default."""
    cfg = fees.config()
    return BrokersResponse(
        default=cfg.default_broker,
        brokers=[BrokerInfo(id=bid, name=fee.name) for bid, fee in cfg.brokers.items()],
    )


@router.post("/envelopes/eligible", response_model=EligibleEnvelopesResponse)
async def list_eligible_envelopes(
    req: EligibilityRequest,
    user: User = Depends(current_active_user),
) -> EligibleEnvelopesResponse:
    """Returns the envelope catalog with eligibility status for this profile."""
    cfg = envelopes.config()
    results = []
    for eid, env in cfg.envelopes.items():
        eligible, note = envelopes.check_eligibility(env, req.age, req.rfr, req.fiscal_shares)
        results.append(
            EnvelopeEligibility(
                id=eid,
                name=env.name,
                rate_pct=env.rate_pct,
                ceiling_eur=env.ceiling_eur,
                tax_status=env.tax_status,
                liquidity_days=env.liquidity_days,
                eligible=eligible,
                note=note,
            )
        )
    return EligibleEnvelopesResponse(envelopes=results)
