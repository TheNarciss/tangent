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
from .aggregator.types import INVEST_ACCOUNT_TYPES as _INVEST_ACCOUNT_TYPES
from .aggregator.types import LOAN_ACCOUNT_TYPES as _LOAN_ACCOUNT_TYPES
from .auth import User, current_active_user
from .db import get_session
from .db.models import BankAccount as _BankAccountRow
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


# Every AccountType lands in exactly one Wealth bucket (cf. aggregator/types.py
# groupings). OTHER is the only type left out: its balance means nothing
# without a type, so it is logged and skipped.
_CASH_TYPES = {
    _AccountType.CHECKING,
    _AccountType.SAVINGS,
    _AccountType.CARD,  # deferred-debit card: negative balance = pending debits
    _AccountType.DEPOSIT,
    _AccountType.JOINT,
}
_INVESTMENT_TYPES = _INVEST_ACCOUNT_TYPES | {_AccountType.CRYPTO}
_LOAN_TYPES = _LOAN_ACCOUNT_TYPES


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


def _loan_outstanding(acc: _BankAccountRow, loan_dict: dict) -> float:
    """Capital still owed on a loan-like account.

    Powens exposes it as `used_amount` (hot column on the loans row, mirrored
    in raw_data.loan). The account balance (negative) is only a fallback.
    """
    loan_row = acc.loan
    used = _safe_float(loan_row.used_amount) if loan_row is not None else None
    if used is None:
        used = _safe_float(loan_dict.get("used_amount"))
    if used is not None and used > 0:
        return used
    return abs(float(acc.balance or 0))


async def get_user_wealth(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> _Wealth:
    """Build the user's complete Wealth snapshot from bank_accounts + holdings.

    Logic (every AccountType is covered, cf. aggregator/types.py):
    - CHECKING / SAVINGS / CARD / DEPOSIT / JOINT → CashAccount
    - LIVRET_* / LDDS / LEP / PEL / CEL / CSL / CAT → WealthEnvelope (enriched
      with metadata from envelopes.yaml)
    - PEA / CTO / LIFE_INSURANCE / CAPITALISATION / PER / PERP / PERCO /
      MADELIN / ARTICLE_83 / PEE / RSP / REAL_ESTATE / CROWDLENDING / CRYPTO
      → InvestmentAccount with positions when the provider lists them, else
      valued at the account balance (`valuation` if Powens sent one); a PEA
      sub-account with 0 holdings is a CashAccount(is_pea_cash=True)
    - LOAN / MORTGAGE / CONSUMER_CREDIT / REVOLVING_CREDIT → Loan, outstanding
      = `used_amount` (fallback |balance|)
    - OTHER → ignored (debug log)
    """
    bank_accounts = await _accounts_repo.list_accounts(session, user.id)

    wealth = _Wealth(
        user_id=user.id,
        snapshot_at=_datetime.now(tz=UTC),
    )

    for acc in bank_accounts:
        acc_type = _AccountType(acc.type)
        institution = acc.institution_name

        if acc_type in _CASH_TYPES:
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
                    balance=float(acc.valuation if acc.valuation is not None else acc.balance or 0),
                    positions=[
                        _WealthPosition(
                            ticker=h.ticker,
                            label=h.label or h.ticker,
                            isin=h.isin,
                            quantity=float(h.quantity),
                            avg_cost=float(h.unit_price),
                            current_value=float(h.current_value),
                            currency=h.currency or "EUR",
                            ter=h.ter,
                            ter_source_url=h.ter_source_url,
                        )
                        for h in holdings
                        if float(h.quantity) > 0
                    ],
                )
            )
            continue

        if acc_type in _LOAN_TYPES:
            raw = acc.raw_data or {}
            raw_loan = raw.get("loan")
            loan_dict: dict = raw_loan if isinstance(raw_loan, dict) else {}
            rate_raw = loan_dict.get("rate")
            # Powens "rate" is in percent (e.g. 1.5 for 1.5%) — convert to decimal
            rate_pct: float | None = None
            if isinstance(rate_raw, (int, float)):
                rate_pct = float(rate_raw) / 100

            wealth.loans.append(
                _Loan(
                    provider_account_id=acc.provider_account_id,
                    institution_name=institution,
                    name=acc.name,
                    outstanding_balance=_loan_outstanding(acc, loan_dict),
                    currency=acc.currency or "EUR",
                    interest_rate_pct=rate_pct,
                    monthly_payment=_safe_float(loan_dict.get("next_payment_amount")),
                    next_payment_date=_parse_date(loan_dict.get("next_payment_date")),
                    deferral_until=_parse_date(loan_dict.get("deferred_until")),
                    maturity_date=_parse_date(loan_dict.get("maturity_date")),
                )
            )
            continue

        logger.debug("get_user_wealth: ignored account type=%s name=%r", acc_type.value, acc.name)

    return wealth
