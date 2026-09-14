"""Enable Banking → neutral DTOs, and the per-session sync.

One `EnableBankingSession` row = one consent at one bank for one user. The
accounts it exposes carry the row id in `raw_data["enablebanking_session"]`,
the way Powens accounts carry `id_connection`, so a row can be unlinked with
its accounts.

An account's `uid` is scoped to the session: the next consent gives the same
account another uid. Its `identification_hash` is the stable identity Enable
Banking provides for exactly that, so it is our provider_account_id and the
uid only serves the API calls of the day.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..aggregator.types import AccountType, BankAccount, Investment, SyncResult, Transaction
from ..db.models import EnableBankingSession
from ..finance import categorization
from ..powens.crypto import decrypt_token
from .client import EnableBankingClient, EnableBankingError

logger = logging.getLogger(__name__)

PROVIDER = "enablebanking"
SAFE_WINDOW_DAYS = 89  # what PSD2 guarantees once the consent's first minutes are gone

# ISO 20022 cash account types → our taxonomy. Anything else is a current account.
_ACCOUNT_TYPES = {
    "CACC": AccountType.CHECKING,
    "TRAN": AccountType.CHECKING,
    "CASH": AccountType.CHECKING,
    "SVGS": AccountType.SAVINGS,
    "CARD": AccountType.CARD,
}

# Which balance is « the » balance, best first: closing booked, interim booked,
# then the available ones, then whatever the bank sends.
_BALANCE_PREFERENCE = ("CLBD", "ITBD", "CLAV", "ITAV", "XPCD", "OPBD", "PRCD")


def account_type(acc: dict) -> AccountType:
    return _ACCOUNT_TYPES.get(str(acc.get("cash_account_type") or "").upper(), AccountType.CHECKING)


def pick_balance(balances: list[dict]) -> float | None:
    """The booked balance when the bank sends one, else the best available."""
    by_type = {str(b.get("balance_type") or "").upper(): b for b in balances}
    for kind in _BALANCE_PREFERENCE:
        if kind in by_type:
            return _amount(by_type[kind].get("balance_amount"))
    return _amount(balances[0].get("balance_amount")) if balances else None


def _amount(value: Any) -> float | None:
    if not isinstance(value, dict) or value.get("amount") in (None, ""):
        return None
    return float(value["amount"])


def account_dto(
    acc: dict,
    *,
    balance: float | None,
    institution_name: str,
    session_key: str,
    synced_at: datetime,
) -> BankAccount:
    ids = acc.get("account_id") or {}
    currency = str(acc.get("currency") or "EUR").upper()
    name = acc.get("name") or acc.get("product") or f"{institution_name} {currency}"
    return BankAccount(
        provider=PROVIDER,
        provider_account_id=account_key(acc),
        name=str(name),
        type=account_type(acc),
        currency=currency,
        institution_name=institution_name,
        iban=ids.get("iban") if isinstance(ids, dict) else None,
        balance=balance if balance is not None else 0.0,
        usage=acc.get("usage"),
        last_synced_at=synced_at,
        raw_data={**acc, "enablebanking_session": session_key},
    )


def disambiguate(accounts: list[BankAccount]) -> list[BankAccount]:
    """Revolut names every pocket after its holder: tell them apart by currency and kind."""
    names = [a.name for a in accounts]
    for acc in accounts:
        if names.count(acc.name) > 1:
            kind = " épargne" if acc.type == AccountType.SAVINGS else ""
            acc.name = f"{acc.institution_name} {acc.currency}{kind}"
    seen: dict[str, int] = {}
    for acc in accounts:
        seen[acc.name] = seen.get(acc.name, 0) + 1
        if seen[acc.name] > 1:
            acc.name = f"{acc.name} ({seen[acc.name]})"
    return accounts


def account_key(acc: dict) -> str:
    """The identity that survives a new consent: the hash, else the session's uid.

    Enable Banking's hash is long and its first 80 characters are the same for
    every account of a bank (they describe the fields hashed): only a digest of
    the whole fits the 64-character column without losing what distinguishes.
    """
    hash_ = acc.get("identification_hash")
    if hash_:
        return hashlib.sha256(str(hash_).encode()).hexdigest()
    return str(acc["uid"])[:64]


def transaction_id(tx: dict) -> str:
    """The bank's reference when it gives one; otherwise a stable hash of the facts."""
    ref = tx.get("entry_reference")
    if ref:
        return str(ref)[:64]
    facts = "|".join(
        str(tx.get(k) or "")
        for k in ("booking_date", "transaction_date", "value_date", "credit_debit_indicator")
    )
    amount = tx.get("transaction_amount") or {}
    facts += f"|{amount.get('amount')}|{amount.get('currency')}|{_description(tx)}"
    return hashlib.sha256(facts.encode()).hexdigest()[:32]


def _description(tx: dict) -> str:
    remittance = tx.get("remittance_information")
    if isinstance(remittance, list):
        text = " ".join(str(r) for r in remittance if r).strip()
        if text:
            return text
    party = tx.get("creditor") if tx.get("credit_debit_indicator") == "DBIT" else tx.get("debtor")
    if isinstance(party, dict) and party.get("name"):
        return str(party["name"])
    return ""


def transaction_dto(tx: dict, *, account_uid: str) -> Transaction | None:
    """Booked transactions only; pending ones move and would duplicate."""
    if str(tx.get("status") or "BOOK").upper() == "PDNG":
        return None
    raw_date = tx.get("booking_date") or tx.get("transaction_date") or tx.get("value_date")
    if not raw_date:
        return None
    amount = _amount(tx.get("transaction_amount"))
    if amount is None:
        return None
    if str(tx.get("credit_debit_indicator") or "").upper() == "DBIT":
        amount = -abs(amount)
    money = tx.get("transaction_amount") or {}
    category = categorization.decide(
        mcc=tx.get("merchant_category_code"), bank_code=tx.get("bank_transaction_code")
    )
    return Transaction(
        provider=PROVIDER,
        provider_transaction_id=transaction_id(tx),
        provider_account_id=account_uid,
        amount=amount,
        currency=str(money.get("currency") or "EUR").upper(),
        transaction_date=date.fromisoformat(str(raw_date)[:10]),
        description=_description(tx),
        category=category,
        category_source=categorization.SOURCE if category else None,
        raw_data=tx,
    )


class EnableBankingAggregator:
    """IBankAggregator for one Enable Banking session (one bank, one consent)."""

    provider_name: str = PROVIDER

    def __init__(
        self,
        *,
        session_id: str,
        session_key: str,
        institution_name: str,
        user_id: uuid.UUID,
        since: date,
    ) -> None:
        self._session_id = session_id
        self._session_key = session_key
        self._institution = institution_name
        self._user_id = user_id
        self._since = since

    async def get_accounts(self) -> list[BankAccount]:
        """A session lists uids (plus an identification hash); each account's
        details come from their own endpoint."""
        synced_at = datetime.now(UTC)
        async with EnableBankingClient() as client:
            data = await client.get_session(self._session_id)
            out: list[BankAccount] = []
            seen: set[str] = set()
            for entry in data.get("accounts_data") or data.get("accounts") or []:
                uid = entry if isinstance(entry, str) else (entry or {}).get("uid")
                if not uid:
                    continue
                acc = await client.get_account_details(str(uid))
                acc["uid"] = str(uid)
                if isinstance(entry, dict) and entry.get("identification_hash"):
                    acc.setdefault("identification_hash", entry["identification_hash"])
                if account_key(acc) in seen:
                    # Two pockets the bank hashes alike: the second keeps its uid.
                    acc.pop("identification_hash", None)
                seen.add(account_key(acc))
                try:
                    balances = await client.get_balances(str(acc["uid"]))
                except EnableBankingError as exc:
                    logger.warning("Enable Banking: balances de %s illisibles: %s", acc["uid"], exc)
                    balances = []
                out.append(
                    account_dto(
                        acc,
                        balance=pick_balance(balances),
                        institution_name=self._institution,
                        session_key=self._session_key,
                        synced_at=synced_at,
                    )
                )
        return disambiguate(out)

    async def get_investments(self, account_id: str) -> list[Investment]:
        return []  # Account information only; no securities through this channel yet.

    async def get_transactions(
        self, account_id: str, limit: int = 100, *, key: str | None = None
    ) -> list[Transaction]:
        """`account_id` is the session's uid (what the API wants); `key` the stable
        provider_account_id the transactions are filed under."""
        async with EnableBankingClient() as client:
            try:
                rows = await client.get_transactions(account_id, date_from=self._since)
            except EnableBankingError as exc:
                # Some banks refuse a window older than what PSD2 guarantees
                # (90 days): ask for that much rather than nothing.
                shorter = date.today() - timedelta(days=SAFE_WINDOW_DAYS)
                if exc.status != 400 or self._since >= shorter:
                    raise
                logger.info(
                    "Enable Banking: fenêtre refusée depuis %s, relecture depuis %s",
                    self._since,
                    shorter,
                )
                rows = await client.get_transactions(account_id, date_from=shorter)
        out: list[Transaction] = []
        for tx in rows:
            try:
                dto = transaction_dto(tx, account_uid=key or account_id)
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Enable Banking: transaction illisible ignorée: %s", exc)
                continue
            if dto:
                out.append(dto)
        with_mcc = sum(1 for tx in rows if tx.get("merchant_category_code"))
        logger.info(
            "Enable Banking: %d opérations lues, %d avec code MCC, %d catégorisées par règle",
            len(rows),
            with_mcc,
            sum(1 for d in out if d.category),
        )
        return out

    async def sync(self) -> SyncResult:
        """Accounts first; an account whose transactions fail is kept, with its error noted."""
        now = datetime.now(UTC)
        try:
            accounts = await self.get_accounts()
        except EnableBankingError as exc:
            logger.warning("Enable Banking sync failed for user=%s: %s", self._user_id, exc)
            return SyncResult(success=False, provider=PROVIDER, error=str(exc), synced_at=now)

        transactions: list[Transaction] = []
        failures: list[str] = []
        for acc in accounts:
            try:
                transactions.extend(
                    await self.get_transactions(
                        str(acc.raw_data["uid"]), key=acc.provider_account_id
                    )
                )
            except EnableBankingError as exc:
                logger.warning("Enable Banking: opérations de %s illisibles: %s", acc.name, exc)
                failures.append(f"{acc.name}: {exc}")
        return SyncResult(
            success=True,
            provider=PROVIDER,
            accounts=accounts,
            transactions=transactions,
            error="; ".join(failures) or None,
            synced_at=now,
        )

    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ignored"}


def is_expired(row: EnableBankingSession, now: datetime | None = None) -> bool:
    return row.valid_until <= (now or datetime.now(UTC))


async def sync_row(db: AsyncSession, row: EnableBankingSession, *, since: date) -> SyncResult:
    """Run one session's sync and record the outcome on its row (committed by the caller)."""
    aggregator = EnableBankingAggregator(
        session_id=decrypt_token(row.encrypted_session_id),
        session_key=str(row.id),
        institution_name=row.bank_name,
        user_id=row.user_id,
        since=since,
    )
    result = await aggregator.sync()
    if result.success:
        row.last_sync_at = result.synced_at
    row.last_error = result.error
    return result
