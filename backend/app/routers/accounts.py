"""Bank account routes — multi-account aggregation (Phase A, ADR-008, ADR-013).

All endpoints filtered by current_active_user + per-user filter in the repos.

POST /accounts/sync also writes to the legacy `positions` table as a bridge,
so the dashboard/historique/optimisation tabs (which still read from the
legacy Portfolio model) keep working while we migrate them to read from
account_holdings directly. To be removed once the migration is complete.

A1 smart sync (5-min cache + force-refresh):
- POST /accounts/sync       → returns cached result if < 5 min old, else syncs
- POST /accounts/refresh    → bypasses cache + asks Powens to re-sync with bank
                              (slow, ~10-30s, but ensures fresh data from bank)

ADR-013 (hot + JSONB):
- BankAccountResponse exposes all hot fields stored on the BankAccount row
  (valuation, diff, coming, ownership, …) plus a nested LoanResponse when
  the account has a Loan attached (one-to-one).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..aggregator import AccountType, Investment, Transaction
from ..auth import User, current_active_user
from ..db import get_session
from ..db.models import BankAccount, PowensCredential
from ..powens.aggregator import PowensAggregator
from ..powens.client import PowensClient, PowensError
from ..powens.crypto import decrypt_token
from ..repositories import account_holdings as holdings_repo
from ..repositories import bank_accounts as accounts_repo
from ..repositories import bank_transactions as bank_txs_repo
from ..repositories import portfolio as portfolio_repo
from ..sync_cache import sync_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["accounts"])


# Wait time after triggering Powens force_sync before re-fetching data.
# Powens typically completes a bank sync in 5-30s depending on the bank.
# 10s is a compromise: long enough to catch most syncs, short enough that
# the user doesn't think the UI is frozen.
POWENS_REFRESH_WAIT_SECONDS = 10


# ── Pydantic response models ────────────────────────────────────────────────


class LoanResponse(BaseModel):
    """Loan sub-resource — attached to a BankAccount of loan-like type."""

    total_amount: float | None
    available_amount: float | None
    used_amount: float | None
    subscription_date: date | None
    maturity_date: date | None
    start_repayment_date: date | None
    deferred: bool | None
    next_payment_amount: float | None
    next_payment_date: date | None
    last_payment_amount: float | None
    last_payment_date: date | None
    nb_payments_done: int | None
    nb_payments_left: int | None
    nb_payments_total: int | None
    rate: float | None
    duration_months: int | None
    insurance_label: str | None
    insurance_amount: float | None
    insurance_rate: float | None
    account_label: str | None
    loan_type: str | None


class BankAccountResponse(BaseModel):
    """Full bank account response — exposes all hot fields stored per ADR-013."""

    id: uuid.UUID
    provider: str
    provider_account_id: str

    # Identification
    name: str
    type: AccountType
    currency: str
    institution_name: str | None

    # Identifiers
    iban: str | None
    bic: str | None
    number: str | None

    # Balance & valuation
    balance: float
    valuation: float | None
    coming: float | None
    coming_balance: float | None

    # Gain/loss (Powens-computed for invest accounts)
    diff: float | None
    diff_percent: float | None
    prev_diff: float | None
    prev_diff_percent: float | None

    # Context
    usage: str | None
    ownership: str | None
    company_name: str | None
    opening_date: date | None

    # State
    bookmarked: bool
    display: bool

    # Sync tracking
    last_synced_at: datetime | None

    # Nested loan (one-to-one) — populated when type is loan-like
    loan: LoanResponse | None = None


class HoldingResponse(BaseModel):
    id: uuid.UUID
    bank_account_id: uuid.UUID
    provider_investment_id: str
    ticker: str
    isin: str | None
    label: str
    quantity: float
    unit_price: float
    current_value: float
    currency: str


class TransactionResponse(BaseModel):
    id: uuid.UUID
    bank_account_id: uuid.UUID
    provider_transaction_id: str
    amount: float
    currency: str
    transaction_date: date
    description: str
    category: str | None


class SyncReport(BaseModel):
    """Outcome of POST /accounts/sync (and /accounts/refresh)."""

    success: bool
    accounts_persisted: int = 0
    holdings_persisted: int = 0
    transactions_persisted: int = 0
    legacy_positions_synced: int = 0
    error: str | None = None
    synced_at: datetime
    from_cache: bool = False


# ── Response builder helpers ────────────────────────────────────────────────


def _loan_to_response(loan) -> LoanResponse:
    return LoanResponse(
        total_amount=loan.total_amount,
        available_amount=loan.available_amount,
        used_amount=loan.used_amount,
        subscription_date=loan.subscription_date,
        maturity_date=loan.maturity_date,
        start_repayment_date=loan.start_repayment_date,
        deferred=loan.deferred,
        next_payment_amount=loan.next_payment_amount,
        next_payment_date=loan.next_payment_date,
        last_payment_amount=loan.last_payment_amount,
        last_payment_date=loan.last_payment_date,
        nb_payments_done=loan.nb_payments_done,
        nb_payments_left=loan.nb_payments_left,
        nb_payments_total=loan.nb_payments_total,
        rate=loan.rate,
        duration_months=loan.duration_months,
        insurance_label=loan.insurance_label,
        insurance_amount=loan.insurance_amount,
        insurance_rate=loan.insurance_rate,
        account_label=loan.account_label,
        loan_type=loan.loan_type,
    )


def _bank_account_to_response(r: BankAccount) -> BankAccountResponse:
    """Convert an ORM BankAccount row to a Pydantic response, including nested Loan."""
    return BankAccountResponse(
        id=r.id,
        provider=r.provider,
        provider_account_id=r.provider_account_id,
        name=r.name,
        type=AccountType(r.type),
        currency=r.currency,
        institution_name=r.institution_name,
        iban=r.iban,
        bic=r.bic,
        number=r.number,
        balance=r.balance,
        valuation=r.valuation,
        coming=r.coming,
        coming_balance=r.coming_balance,
        diff=r.diff,
        diff_percent=r.diff_percent,
        prev_diff=r.prev_diff,
        prev_diff_percent=r.prev_diff_percent,
        usage=r.usage,
        ownership=r.ownership,
        company_name=r.company_name,
        opening_date=r.opening_date,
        bookmarked=r.bookmarked,
        display=r.display,
        last_synced_at=r.last_synced_at,
        loan=_loan_to_response(r.loan) if r.loan else None,
    )


# ── Read routes ─────────────────────────────────────────────────────────────


@router.get("", response_model=list[BankAccountResponse])
async def list_accounts(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[BankAccountResponse]:
    """All bank accounts owned by the current user (with nested loan if any)."""
    rows = await accounts_repo.list_accounts(session, user.id)
    return [_bank_account_to_response(r) for r in rows]


@router.get("/{account_id}", response_model=BankAccountResponse)
async def get_account(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> BankAccountResponse:
    row = await accounts_repo.get_account(session, user.id, account_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return _bank_account_to_response(row)


@router.get("/{account_id}/holdings", response_model=list[HoldingResponse])
async def list_holdings(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[HoldingResponse]:
    if (await accounts_repo.get_account(session, user.id, account_id)) is None:
        raise HTTPException(status_code=404, detail="Account not found")
    rows = await holdings_repo.list_holdings(session, user.id, account_id)
    return [
        HoldingResponse(
            id=r.id,
            bank_account_id=r.bank_account_id,
            provider_investment_id=r.provider_investment_id,
            ticker=r.ticker,
            isin=r.isin,
            label=r.label,
            quantity=r.quantity,
            unit_price=r.unit_price,
            current_value=r.current_value,
            currency=r.currency,
        )
        for r in rows
    ]


@router.get("/{account_id}/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    account_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=500),
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[TransactionResponse]:
    if (await accounts_repo.get_account(session, user.id, account_id)) is None:
        raise HTTPException(status_code=404, detail="Account not found")
    rows = await bank_txs_repo.list_transactions(
        session,
        user.id,
        account_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return [
        TransactionResponse(
            id=r.id,
            bank_account_id=r.bank_account_id,
            provider_transaction_id=r.provider_transaction_id,
            amount=r.amount,
            currency=r.currency,
            transaction_date=r.transaction_date,
            description=r.description,
            category=r.category,
        )
        for r in rows
    ]


# ── Sync routes ─────────────────────────────────────────────────────────────


@router.post("/sync", response_model=SyncReport)
async def sync_accounts(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> SyncReport:
    """End-to-end sync. Returns cached result if < 5 min old.

    To force a real Powens sync (e.g. user wants the absolute latest balance
    from their bank), use POST /accounts/refresh instead.
    """
    cached = await sync_cache.get_fresh(user.id)
    if cached is not None:
        logger.info("sync_accounts user=%s: returning cached result", user.id)
        return cached.model_copy(update={"from_cache": True})

    report = await _do_sync(user, session)
    await sync_cache.set(user.id, report)
    return report


@router.post("/refresh", response_model=SyncReport)
async def refresh_accounts(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> SyncReport:
    """Force Powens to re-sync with the bank, then fetch the latest data.

    This is what the user wants when the cached/displayed balance doesn't
    match what they see in their bank's app. Slow (~10-30s total). Use sparingly.

    Note: Powens enforces its own Fair Usage Policy on force_sync calls; if
    a sync was already triggered recently, we get a 409 and we silently
    continue with the data Powens already has.
    """
    stmt = select(PowensCredential).where(PowensCredential.user_id == user.id)
    res = await session.execute(stmt)
    cred = res.scalars().first()
    if cred is None:
        raise HTTPException(
            status_code=400,
            detail="No Powens connection. Connect Powens first.",
        )

    token = decrypt_token(cred.encrypted_token)

    # 1. Force every connection to re-sync with its bank
    triggered_count = 0
    async with PowensClient(token=token) as client:
        try:
            connections = await client.get_connections()
        except PowensError as exc:
            logger.warning("refresh user=%s: get_connections failed: %s", user.id, exc)
            connections = []

        for conn in connections:
            conn_id = conn.get("id")
            if not isinstance(conn_id, int):
                continue
            try:
                await client.force_sync(conn_id)
                triggered_count += 1
                logger.info(
                    "refresh user=%s: triggered Powens force_sync conn=%s",
                    user.id,
                    conn_id,
                )
            except PowensError as exc:
                # 409 = sync already in progress / rate-limited — that's fine
                logger.info(
                    "refresh user=%s: force_sync conn=%s skipped (%s)",
                    user.id,
                    conn_id,
                    exc,
                )

    # 2. Give Powens time to talk to the bank
    if triggered_count > 0:
        logger.info(
            "refresh user=%s: waiting %ds for Powens to finish",
            user.id,
            POWENS_REFRESH_WAIT_SECONDS,
        )
        await asyncio.sleep(POWENS_REFRESH_WAIT_SECONDS)

    # 3. Bypass cache and run a real sync
    await sync_cache.invalidate(user.id)
    report = await _do_sync(user, session)
    await sync_cache.set(user.id, report)
    return report


# ── Internal sync helper ────────────────────────────────────────────────────


async def _do_sync(user: User, session: AsyncSession) -> SyncReport:
    """Actual sync logic — no cache check, always hits Powens.

    Extracted so /sync and /refresh can share it.
    """
    stmt = select(PowensCredential).where(PowensCredential.user_id == user.id)
    res = await session.execute(stmt)
    cred = res.scalars().first()
    if cred is None:
        raise HTTPException(
            status_code=400,
            detail="No Powens connection. Connect Powens first.",
        )

    token = decrypt_token(cred.encrypted_token)
    aggregator = PowensAggregator(token=token, user_id=user.id, session=session)
    result = await aggregator.sync()

    if not result.success:
        return SyncReport(success=False, error=result.error, synced_at=result.synced_at)

    # Persist accounts (BankAccount + nested Loan upsert if applicable)
    account_id_map: dict[str, uuid.UUID] = {}
    persisted_accounts = 0
    for acc_dto in result.accounts:
        orm = await accounts_repo.upsert_account(session, user.id, acc_dto)
        account_id_map[acc_dto.provider_account_id] = orm.id
        persisted_accounts += 1

    holdings_by_acc: dict[str, list[Investment]] = {}
    for inv in result.investments:
        holdings_by_acc.setdefault(inv.provider_account_id, []).append(inv)

    txs_by_acc: dict[str, list[Transaction]] = {}
    for tx in result.transactions:
        txs_by_acc.setdefault(tx.provider_account_id, []).append(tx)

    persisted_holdings = 0
    for prov_acc_id, holdings in holdings_by_acc.items():
        if prov_acc_id in account_id_map:
            persisted = await holdings_repo.replace_holdings(
                session, user.id, account_id_map[prov_acc_id], holdings
            )
            persisted_holdings += len(persisted)

    persisted_txs = 0
    for prov_acc_id, txs in txs_by_acc.items():
        if prov_acc_id in account_id_map:
            inserted = await bank_txs_repo.upsert_transactions(
                session, user.id, account_id_map[prov_acc_id], txs
            )
            persisted_txs += inserted

    # ── Legacy bridge: sync to portfolios/positions table ────────────────────
    # The legacy dashboard/historique/optimisation routes still read from this
    # table. Until we migrate them, derive legacy data from the new sync result.
    legacy_positions_count = await _sync_to_legacy_portfolio(session, user.id, result)

    logger.info(
        "Sync user=%s: %d accounts, %d holdings, %d new txs, %d legacy positions",
        user.id,
        persisted_accounts,
        persisted_holdings,
        persisted_txs,
        legacy_positions_count,
    )

    return SyncReport(
        success=True,
        accounts_persisted=persisted_accounts,
        holdings_persisted=persisted_holdings,
        transactions_persisted=persisted_txs,
        legacy_positions_synced=legacy_positions_count,
        synced_at=result.synced_at,
        from_cache=False,
    )


# ── Internal: legacy bridge ─────────────────────────────────────────────────


_INVESTMENT_ACCOUNT_TYPES = {
    AccountType.PEA,
    AccountType.CTO,
    AccountType.LIFE_INSURANCE,
}

_CASH_NAME_HINTS = ("espèces", "especes", "cash", "liquidités", "liquidites")


def _is_pea_cash_account(acc) -> bool:
    """Heuristic: a PEA sub-account named 'Espèces' / 'Cash' holds cash, not titles."""
    if acc.type != AccountType.PEA:
        return False
    name_lower = (acc.name or "").lower()
    return any(hint in name_lower for hint in _CASH_NAME_HINTS)


async def _sync_to_legacy_portfolio(
    session: AsyncSession,
    user_id: uuid.UUID,
    result,
) -> int:
    """Derive legacy Position list from the multi-account sync result and persist."""
    positions_by_ticker: dict[str, dict] = {}
    for inv in result.investments:
        if inv.quantity <= 0:
            continue
        if inv.ticker in positions_by_ticker:
            existing = positions_by_ticker[inv.ticker]
            total_qty = existing["quantity"] + inv.quantity
            if total_qty > 0:
                weighted_cost = (
                    existing["quantity"] * existing["avg_cost"] + inv.quantity * inv.unit_price
                ) / total_qty
            else:
                weighted_cost = 0.0
            existing["quantity"] = total_qty
            existing["avg_cost"] = weighted_cost
        else:
            positions_by_ticker[inv.ticker] = {
                "ticker": inv.ticker,
                "quantity": float(inv.quantity),
                "avg_cost": float(inv.unit_price),
                "isin": inv.isin,
                "label": inv.label,
            }

    cash = 0.0
    for acc in result.accounts:
        if _is_pea_cash_account(acc):
            cash += float(acc.balance)

    legacy_positions = list(positions_by_ticker.values())

    await portfolio_repo.replace_positions(
        session,
        user_id,
        new_positions=legacy_positions,
        cash=cash,
    )
    return len(legacy_positions)
