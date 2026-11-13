"""Finverse → neutral DTOs, and the per-connection sync (ADR-037).

A `FinverseConnection` row = one bank linked in Finverse Link for one user.
Its accounts carry the row id in `raw_data["finverse_connection"]`, the way
Enable Banking accounts carry their session, so a row is unlinked with its
accounts. Amounts come signed as we store them: negative for a debit.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime

from ..aggregator.types import (
    LOAN_ACCOUNT_TYPES,
    AccountType,
    BankAccount,
    SyncResult,
    Transaction,
)
from ..db.models import FinverseConnection
from ..powens.crypto import decrypt_token, encrypt_token
from .client import FinverseClient, FinverseError

logger = logging.getLogger(__name__)

PROVIDER = "finverse"

# Finverse sub-types → our taxonomy. Securities, funds and bonds stay
# `other`: no holdings come with them, and our wrappers (PEA, CTO) carry
# French rules that would not hold.
_SUBTYPES = {
    "CURRENT": AccountType.CHECKING,
    "SAVINGS": AccountType.SAVINGS,
    "TIME_DEPOSIT": AccountType.DEPOSIT,
    "CREDIT_CARD": AccountType.CARD,
    "DEBIT_CARD": AccountType.CARD,
    "MORTGAGE": AccountType.MORTGAGE,
    "PERSONAL_LOAN": AccountType.LOAN,
}
_TYPES = {"DEPOSIT": AccountType.CHECKING, "CARD": AccountType.CARD, "LOAN": AccountType.LOAN}

# What GET /login_identity says once Finverse has read the bank, well or not.
_DONE = {"DATA_RETRIEVAL_COMPLETE", "DATA_RETRIEVAL_PARTIALLY_SUCCESSFUL", "ERROR"}


def _kind(acc: dict) -> dict:
    kind = acc.get("account_type")
    return kind if isinstance(kind, dict) else {}


def _subtype(acc: dict) -> str:
    return str(_kind(acc).get("subtype") or "").upper()


def account_type(acc: dict) -> AccountType:
    subtype = _subtype(acc)
    if subtype in _SUBTYPES:
        return _SUBTYPES[subtype]
    return _TYPES.get(str(_kind(acc).get("type") or "").upper(), AccountType.OTHER)


def _value(amount: object) -> float | None:
    if not isinstance(amount, dict) or amount.get("value") is None:
        return None
    return float(amount["value"])


def account_dto(
    acc: dict, *, institution_name: str, connection_key: str, synced_at: datetime
) -> BankAccount | None:
    """A listed account; closed ones and parents (their children are listed) are skipped."""
    if acc.get("is_closed") or acc.get("is_parent"):
        return None
    balance = acc.get("balance") or {}
    currency = str(
        acc.get("account_currency")
        or (balance.get("currency") if isinstance(balance, dict) else "")
        or "SGD"
    ).upper()[:3]
    kind = account_type(acc)
    value = _value(balance) or 0.0
    # What is owed reads negative, as Powens gives it.
    if kind in LOAN_ACCOUNT_TYPES or _subtype(acc) == "CREDIT_CARD":
        value = -abs(value)
    return BankAccount(
        provider=PROVIDER,
        provider_account_id=str(acc["account_id"])[:64],
        name=str(acc.get("account_nickname") or acc.get("account_name") or institution_name),
        type=kind,
        currency=currency,
        institution_name=institution_name,
        number=acc.get("account_number_masked"),
        balance=value,
        last_synced_at=synced_at,
        raw_data={**acc, "finverse_connection": connection_key},
    )


def transaction_dto(tx: dict, *, currency: str) -> Transaction | None:
    """Posted transactions only; a pending one changes and would duplicate."""
    if tx.get("is_pending"):
        return None
    amount = tx.get("amount") or {}
    value = _value(amount)
    raw_date = tx.get("posted_date") or tx.get("transaction_time") or tx.get("created_at")
    if value is None or not raw_date:
        return None
    return Transaction(
        provider=PROVIDER,
        provider_transaction_id=str(tx["transaction_id"])[:64],
        provider_account_id=str(tx["account_id"])[:64],
        amount=value,
        currency=str(
            (amount.get("currency") if isinstance(amount, dict) else None) or currency
        ).upper()[:3],
        transaction_date=date.fromisoformat(str(raw_date)[:10]),
        description=str(tx.get("description") or tx.get("merchant_name") or ""),
        raw_data=tx,
    )


async def wait_for_data(
    client: FinverseClient, token: str, *, attempts: int = 10, delay: float = 2.0
) -> str:
    """Right after linking Finverse is still reading the bank: wait a little for it."""
    status = "UNKNOWN"
    for attempt in range(attempts):
        data = await client.login_identity(token)
        status = str((data.get("login_identity") or {}).get("status") or "UNKNOWN")
        if status in _DONE:
            break
        if attempt < attempts - 1:
            await asyncio.sleep(delay)
    return status


async def read(client: FinverseClient, token: str, row: FinverseConnection) -> SyncResult:
    """Accounts and transactions of one linked bank, as neutral DTOs."""
    now = datetime.now(UTC)
    data = await client.accounts(token)
    institution = (data.get("institution") or {}).get("institution_name") or row.institution_name
    row.institution_name = str(institution)[:128]
    accounts = [
        dto
        for acc in data.get("accounts") or []
        if (
            dto := account_dto(
                acc,
                institution_name=row.institution_name,
                connection_key=str(row.id),
                synced_at=now,
            )
        )
    ]
    currencies = {a.provider_account_id: a.currency for a in accounts}
    transactions: list[Transaction] = []
    for tx in await client.transactions(token):
        try:
            item = transaction_dto(tx, currency=currencies.get(str(tx.get("account_id")), "SGD"))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Finverse: transaction illisible ignorée: %s", exc)
            continue
        if item and item.provider_account_id in currencies:
            transactions.append(item)
    return SyncResult(
        success=True,
        provider=PROVIDER,
        accounts=accounts,
        transactions=transactions,
        synced_at=now,
    )


async def sync_row(row: FinverseConnection) -> SyncResult:
    """Swap the refresh token for a fresh one, read, record the outcome on the row.

    The row is committed by the caller: a new refresh token must not be lost.
    """
    now = datetime.now(UTC)
    try:
        async with FinverseClient() as client:
            tokens = await client.refresh(decrypt_token(row.encrypted_refresh_token))
            if tokens.get("refresh_token"):
                row.encrypted_refresh_token = encrypt_token(str(tokens["refresh_token"]))
            result = await read(client, str(tokens["access_token"]), row)
    except (FinverseError, KeyError, ValueError) as exc:
        logger.warning("Finverse sync failed for connection=%s: %s", row.id, exc)
        row.last_error = str(exc)[:500]
        return SyncResult(success=False, provider=PROVIDER, error=str(exc), synced_at=now)
    row.last_sync_at = result.synced_at
    row.last_error = None
    return result
