"""Persist a `SyncResult`, whatever aggregator produced it.

Accounts are upserted, holdings replaced, transactions inserted once. On a
first sync the default broker is guessed from the largest investment wrapper.
Shared by the sync routes, the Enable Banking callback and the scheduler.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ..finance import merchants
from ..finance.fees import autodetect_broker
from ..repositories import account_holdings as holdings_repo
from ..repositories import bank_accounts as accounts_repo
from ..repositories import bank_transactions as bank_txs_repo
from ..repositories import profile as profile_repo
from .types import AccountType, Investment, SyncResult, Transaction

logger = logging.getLogger(__name__)

_BROKER_WRAPPERS = {AccountType.PEA, AccountType.CTO, AccountType.LIFE_INSURANCE}


@dataclass(frozen=True)
class Persisted:
    accounts: int = 0
    holdings: int = 0
    transactions: int = 0

    def __add__(self, other: Persisted) -> Persisted:
        return Persisted(
            self.accounts + other.accounts,
            self.holdings + other.holdings,
            self.transactions + other.transactions,
        )


async def persist_sync_result(
    session: AsyncSession, user_id: uuid.UUID, result: SyncResult
) -> Persisted:
    account_id_map: dict[str, uuid.UUID] = {}
    for acc_dto in result.accounts:
        orm = await accounts_repo.upsert_account(session, user_id, acc_dto)
        account_id_map[acc_dto.provider_account_id] = orm.id

    holdings_by_acc: dict[str, list[Investment]] = {}
    for inv in result.investments:
        holdings_by_acc.setdefault(inv.provider_account_id, []).append(inv)
    # What a past decision on the same merchant already settled, before the LLM.
    if any(tx.category is None for tx in result.transactions):
        learned = await bank_txs_repo.learned_categories(session, user_id)
        for tx in result.transactions:
            if tx.category is None:
                known = learned.get(merchants.fold(tx.description))
                if known:
                    tx.category = known
                    tx.category_source = bank_txs_repo.LEARNED_SOURCE

    txs_by_acc: dict[str, list[Transaction]] = {}
    for tx in result.transactions:
        txs_by_acc.setdefault(tx.provider_account_id, []).append(tx)

    holdings_count = 0
    for prov_acc_id, holdings in holdings_by_acc.items():
        if prov_acc_id in account_id_map:
            persisted = await holdings_repo.replace_holdings(
                session, user_id, account_id_map[prov_acc_id], holdings
            )
            holdings_count += len(persisted)

    txs_count = 0
    for prov_acc_id, txs in txs_by_acc.items():
        if prov_acc_id in account_id_map:
            txs_count += await bank_txs_repo.upsert_transactions(
                session, user_id, account_id_map[prov_acc_id], txs
            )

    await _autodetect_broker(session, user_id, result)

    logger.info(
        "Sync user=%s provider=%s: %d accounts, %d holdings, %d new txs",
        user_id,
        result.provider,
        len(account_id_map),
        holdings_count,
        txs_count,
    )
    return Persisted(len(account_id_map), holdings_count, txs_count)


async def _autodetect_broker(session: AsyncSession, user_id: uuid.UUID, result: SyncResult) -> None:
    """First sync: the institution of the largest PEA / CTO / AV becomes the default broker."""
    profile = await profile_repo.get_or_create(session, user_id)
    if profile.default_broker is not None:
        return
    candidates = [
        (acc.institution_name, float(acc.valuation or acc.balance or 0))
        for acc in result.accounts
        if acc.type in _BROKER_WRAPPERS and acc.institution_name
    ]
    if not candidates:
        return
    candidates.sort(key=lambda x: x[1], reverse=True)
    broker_id = autodetect_broker(candidates[0][0])
    if broker_id:
        await profile_repo.update(session, user_id, {"default_broker": broker_id})
        logger.info(
            "Autodetected broker=%s from institution=%r for user=%s",
            broker_id,
            candidates[0][0],
            user_id,
        )
