"""Common FastAPI dependencies — auth + DB session + composite domain objects.

Most endpoints need:
1. The current authenticated user → Depends(current_active_user)
2. A DB session → Depends(get_session)
3. A Portfolio domain object (with positions + cash) built from DB

This module provides the composite dependencies so endpoints stay one-liner
clean instead of repeating glue code.
"""

from __future__ import annotations

import logging
from datetime import UTC
from datetime import date as _date
from datetime import datetime as _datetime

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .aggregator import AccountType as _AccountType
from .auth import User, current_active_user
from .db import get_session
from .finance import envelope_metadata as _envelope_metadata
from .models import (
    CashAccount as _CashAccount,
)
from .models import (
    InvestmentAccount as _InvestmentAccount,
)
from .models import (
    Loan as _Loan,
)
from .models import (
    Wealth as _Wealth,
)
from .models import (
    WealthEnvelope as _WealthEnvelope,
)
from .models import (
    WealthPosition as _WealthPosition,
)
from .repositories import account_holdings as _holdings_repo
from .repositories import bank_accounts as _accounts_repo

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
#  Wealth builder (Phase 2 of the legacy migration)
# ════════════════════════════════════════════════════════════════════════════


# Investment wrappers (have positions inside)
_INVESTMENT_TYPES = {
    _AccountType.PEA,
    _AccountType.CTO,
    _AccountType.LIFE_INSURANCE,
}


def _parse_date(value: str | None) -> _date | None:
    """Parse YYYY-MM-DD from raw_data, tolerant to ISO datetime suffixes."""
    if not value or not isinstance(value, str):
        return None
    try:
        return _date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None


def _safe_float(value: object) -> float | None:
    """Cast to float if value is int/float, else None. Defangs mypy on dict.get()."""
    if isinstance(value, (int, float)):
        return float(value)
    return None


async def get_user_wealth(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> _Wealth:
    """Build the user's complete Wealth snapshot from bank_accounts + holdings.

    Logic:
    - CHECKING / SAVINGS → CashAccount (savings non-réglementé treated as cash)
    - LIVRET_* / LDDS / LEP / PEL / CEL / CSL / CAT → WealthEnvelope (enriched
      with metadata from envelopes.yaml)
    - PEA / CTO / LIFE_INSURANCE → InvestmentAccount with positions, OR
      CashAccount(is_pea_cash=True) for PEA sub-accounts with 0 holdings
    - LOAN → Loan (with details from raw_data.loan if present)
    - OTHER → ignored (with a debug log; covered by Phase 2 PR 6 cleanup)
    """
    bank_accounts = await _accounts_repo.list_accounts(session, user.id)

    wealth = _Wealth(
        user_id=user.id,
        snapshot_at=_datetime.now(tz=UTC),
    )

    for acc in bank_accounts:
        acc_type = _AccountType(acc.type)
        institution = acc.institution_name

        if acc_type in (_AccountType.CHECKING, _AccountType.SAVINGS):
            wealth.checking_accounts.append(
                _CashAccount(
                    provider_account_id=acc.provider_account_id,
                    institution_name=institution,
                    name=acc.name,
                    balance=float(acc.balance or 0),
                    currency=acc.currency or "EUR",
                )
            )
            continue

        if _envelope_metadata.is_envelope_type(acc_type):
            yaml_key = _envelope_metadata.get_envelope_yaml_key(acc_type)
            meta = _envelope_metadata.get_metadata(acc_type)
            wealth.envelopes.append(
                _WealthEnvelope(
                    provider_account_id=acc.provider_account_id,
                    institution_name=institution,
                    name=acc.name,
                    balance=float(acc.balance or 0),
                    envelope_type=yaml_key or acc_type.value,
                    currency=acc.currency or "EUR",
                    display_name=meta.display_name if meta else None,
                    rate_pct=meta.rate_pct if meta else None,
                    ceiling_eur=meta.ceiling_eur if meta else None,
                    tax_status=meta.tax_status if meta else None,
                )
            )
            continue

        if acc_type in _INVESTMENT_TYPES:
            holdings = await _holdings_repo.list_holdings(session, user.id, acc.id)
            if not holdings and acc_type == _AccountType.PEA:
                # PEA sub-account with 0 holdings → cash sub-account
                wealth.pea_cash_accounts.append(
                    _CashAccount(
                        provider_account_id=acc.provider_account_id,
                        institution_name=institution,
                        name=acc.name,
                        balance=float(acc.balance or 0),
                        currency=acc.currency or "EUR",
                        is_pea_cash=True,
                    )
                )
                continue

            wealth.investment_accounts.append(
                _InvestmentAccount(
                    provider_account_id=acc.provider_account_id,
                    institution_name=institution,
                    name=acc.name,
                    account_type=acc_type.value,
                    currency=acc.currency or "EUR",
                    positions=[
                        _WealthPosition(
                            ticker=h.ticker,
                            label=h.label or h.ticker,
                            isin=h.isin,
                            quantity=float(h.quantity),
                            avg_cost=float(h.unit_price),
                            current_value=float(h.current_value),
                            currency=h.currency or "EUR",
                        )
                        for h in holdings
                        if float(h.quantity) > 0
                    ],
                )
            )
            continue

        if acc_type == _AccountType.LOAN:
            raw = acc.raw_data or {}
            loan_dict = raw.get("loan") or {}
            rate_raw = loan_dict.get("rate") if isinstance(loan_dict, dict) else None
            # Powens "rate" is in percent (e.g. 1.5 for 1.5%) — convert to decimal
            rate_pct: float | None = None
            if isinstance(rate_raw, (int, float)):
                rate_pct = float(rate_raw) / 100

            wealth.loans.append(
                _Loan(
                    provider_account_id=acc.provider_account_id,
                    institution_name=institution,
                    name=acc.name,
                    outstanding_balance=abs(float(acc.balance or 0)),
                    currency=acc.currency or "EUR",
                    interest_rate_pct=rate_pct,
                    monthly_payment=_safe_float(
                        loan_dict.get("next_payment_amount")
                        if isinstance(loan_dict, dict)
                        else None
                    ),
                    next_payment_date=_parse_date(
                        loan_dict.get("next_payment_date") if isinstance(loan_dict, dict) else None
                    ),
                    deferral_until=_parse_date(
                        loan_dict.get("deferred_until") if isinstance(loan_dict, dict) else None
                    ),
                    maturity_date=_parse_date(
                        loan_dict.get("maturity_date") if isinstance(loan_dict, dict) else None
                    ),
                )
            )
            continue

        # Other / Unknown → ignored. Will be addressed by AccountType heuristics
        # in a follow-up (the LOAN heuristic for "Vcc - Prêt Jeune" is the first
        # of these fixes).
        import logging  # local import to avoid module-level overhead

        logging.getLogger(__name__).debug(
            "get_user_wealth: ignored account type=%s name=%r", acc_type.value, acc.name
        )

    return wealth
