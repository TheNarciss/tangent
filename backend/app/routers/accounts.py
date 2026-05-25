"""Bank account routes — multi-account aggregation (Phase A3, ADR-008).

All endpoints filtered by current_active_user + per-user filter in the repos.

POST /accounts/sync also writes to the legacy `positions` table as a bridge,
so the dashboard/historique/optimisation tabs (which still read from the
legacy Portfolio model) keep working while we migrate them to read from
account_holdings directly. To be removed once the migration is complete.
"""

from __future__ import annotations

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
from ..db.models import PowensCredential
from ..powens.aggregator import PowensAggregator
from ..powens.crypto import decrypt_token
from ..repositories import account_holdings as holdings_repo
from ..repositories import bank_accounts as accounts_repo
from ..repositories import bank_transactions as bank_txs_repo
from ..repositories import portfolio as portfolio_repo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["accounts"])


# ── Pydantic response models ────────────────────────────────────────────────


class BankAccountResponse(BaseModel):
    id: uuid.UUID
    provider: str
    provider_account_id: str
    name: str
    type: AccountType
    currency: str
    balance: float
    iban: str | None
    institution_name: str | None
    last_synced_at: datetime | None


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
    """Outcome of POST /accounts/sync."""

    success: bool
    accounts_persisted: int = 0
    holdings_persisted: int = 0
    transactions_persisted: int = 0
    legacy_positions_synced: int = 0
    error: str | None = None
    synced_at: datetime


# ── Routes ──────────────────────────────────────────────────────────────────


@router.get("", response_model=list[BankAccountResponse])
async def list_accounts(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[BankAccountResponse]:
    """All bank accounts owned by the current user."""
    rows = await accounts_repo.list_accounts(session, user.id)
    return [
        BankAccountResponse(
            id=r.id,
            provider=r.provider,
            provider_account_id=r.provider_account_id,
            name=r.name,
            type=AccountType(r.type),
            currency=r.currency,
            balance=r.balance,
            iban=r.iban,
            institution_name=r.institution_name,
            last_synced_at=r.last_synced_at,
        )
        for r in rows
    ]


@router.get("/{account_id}", response_model=BankAccountResponse)
async def get_account(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> BankAccountResponse:
    row = await accounts_repo.get_account(session, user.id, account_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return BankAccountResponse(
        id=row.id,
        provider=row.provider,
        provider_account_id=row.provider_account_id,
        name=row.name,
        type=AccountType(row.type),
        currency=row.currency,
        balance=row.balance,
        iban=row.iban,
        institution_name=row.institution_name,
        last_synced_at=row.last_synced_at,
    )


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


@router.post("/sync", response_model=SyncReport)
async def sync_accounts(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> SyncReport:
    """End-to-end sync: PowensAggregator → persist into bank_accounts/holdings/transactions.

    Also syncs into the legacy `positions` table as a bridge, so dashboard/
    historique/optimisation tabs keep working until they're migrated to read
    from account_holdings directly.
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

    # Persist into the new multi-account tables (idempotent)
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
    """Derive legacy Position list from the multi-account sync result and persist.

    Aggregates holdings across all investment accounts by ticker (weighted-average
    avg_cost if the same ticker appears in multiple accounts). Cash is the sum
    of all PEA Espèces / Cash account balances.

    Returns the number of legacy positions written.
    """
    # Build ticker → aggregated position
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

    # Sum PEA cash balances
    cash = 0.0
    for acc in result.accounts:
        if _is_pea_cash_account(acc):
            cash += float(acc.balance)

    legacy_positions = list(positions_by_ticker.values())

    # Always write, even if empty — this also clears stale legacy positions
    # when the user has no more investments (idempotent overwrite).
    await portfolio_repo.replace_positions(
        session,
        user_id,
        new_positions=legacy_positions,
        cash=cash,
    )
    return len(legacy_positions)
