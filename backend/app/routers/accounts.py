"""Bank account routes — multi-account aggregation (Phase A3, ADR-008).

All endpoints filtered by current_active_user + per-user filter in the repos.
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
    """End-to-end sync: PowensAggregator → persist into bank_accounts/holdings/transactions."""
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

    # Persist via repositories (idempotent)
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

    logger.info(
        "Sync user=%s: %d accounts, %d holdings, %d new txs",
        user.id,
        persisted_accounts,
        persisted_holdings,
        persisted_txs,
    )

    return SyncReport(
        success=True,
        accounts_persisted=persisted_accounts,
        holdings_persisted=persisted_holdings,
        transactions_persisted=persisted_txs,
        synced_at=result.synced_at,
    )
