"""BankAccount + Loan repository — multi-tenant CRUD (ADR-002, ADR-008, ADR-013).

Every method filters by user_id (multi-tenant isolation).
Persistence pattern: hot fields → typed columns, full payload → raw_data JSONB.

When the DTO has a nested `loan` (loan-like accounts), it is upserted in the
same call to keep BankAccount + Loan transactionally consistent.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..aggregator import BankAccount as BankAccountDTO
from ..db.models import BankAccount, Loan

logger = logging.getLogger(__name__)


# ── The same account under a new id ────────────────────────────────────────
# Powens numbers accounts per connection: a bank connected again brings the
# same accounts back under new ids, next to the old ones it still lists.
# Enable Banking's ids already survive a new consent (`identification_hash`).
# Only accounts of different connections can be one: a bank never lists an
# account twice in one connection, so two look-alikes there (two loans whose
# masked numbers end alike) are two accounts, and nothing of theirs is merged.
_IDS_PER_CONNECTION = frozenset({"powens"})

_NEVER = datetime.min.replace(tzinfo=UTC)


def _identity(
    kind: str, currency: str, iban: str | None, number: str | None, bank: str | None
) -> tuple[str, ...] | None:
    """What says two ids are one account: its IBAN, else its number at its bank.

    The kind and the currency go with it: a card is not its current account,
    and a multi-currency account can share one IBAN between its pockets.
    """
    if iban and iban.strip():
        return ("iban", kind, currency, "".join(iban.split()).upper())
    if number and number.strip():
        return ("number", kind, currency, (bank or "").casefold(), "".join(number.split()).upper())
    return None


def identity(account: BankAccountDTO) -> tuple[str, ...] | None:
    """The account behind a provider id, for the providers whose ids change; else None."""
    if account.provider not in _IDS_PER_CONNECTION:
        return None
    return _identity(
        account.type.value, account.currency, account.iban, account.number, account.institution_name
    )


def _connection(raw_data: dict | None) -> object:
    return (raw_data or {}).get("id_connection")


def _one_per_connection(connections: list[object]) -> bool:
    """Whether the look-alikes each come from their own connection: then they are one account."""
    return None not in connections and len(set(connections)) == len(connections)


def one_per_account(accounts: list[BankAccountDTO]) -> list[BankAccountDTO]:
    """A bank connected twice lists its accounts twice: keep the freshest of each.

    Freshest is the one the bank read last, then the newest id; the other
    belongs to a connection that no longer reads anything. Order is kept.
    """
    groups: dict[tuple[str, ...], list[BankAccountDTO]] = {}
    for acc in accounts:
        key = identity(acc)
        if key is not None:
            groups.setdefault(key, []).append(acc)
    dropped: set[int] = set()
    for group in groups.values():
        if len(group) > 1 and _one_per_connection([_connection(a.raw_data) for a in group]):
            freshest = max(group, key=_freshness)
            dropped.update(id(a) for a in group if a is not freshest)
    return [acc for acc in accounts if id(acc) not in dropped]


def _freshness(account: BankAccountDTO) -> tuple[datetime, int]:
    pid = account.provider_account_id
    return account.powens_last_update or _NEVER, int(pid) if pid.isdigit() else -1


async def _adopt_oldest_row(
    session: AsyncSession, user_id: uuid.UUID, account_dto: BankAccountDTO
) -> None:
    """Give this id to the account's oldest row; drop the duplicates made since.

    The oldest row carries the history — transactions, categories decided —
    and answers to the new id from now on. A row an earlier sync created for
    the same account under another connection is a duplicate, and goes.
    """
    key = identity(account_dto)
    if key is None:
        return
    rows = (
        (
            await session.execute(
                select(BankAccount).where(
                    BankAccount.user_id == user_id,
                    BankAccount.provider == account_dto.provider,
                )
            )
        )
        .scalars()
        .all()
    )
    same = [
        r
        for r in rows
        if _identity(r.type, r.currency, r.iban, r.number, r.institution_name) == key
    ]
    others = [r for r in same if r.provider_account_id != account_dto.provider_account_id]
    connections = [_connection(account_dto.raw_data)] + [_connection(r.raw_data) for r in others]
    if not others or not _one_per_connection(connections):
        return
    oldest, *newer = sorted(same, key=lambda r: r.created_at)
    for row in newer:
        logger.info("bank_account %s is a duplicate of %s, removed", row.id, oldest.id)
        await session.delete(row)
    await session.flush()
    if oldest.provider_account_id != account_dto.provider_account_id:
        logger.info(
            "bank_account %s recognised under a new id: %s → %s",
            oldest.id,
            oldest.provider_account_id,
            account_dto.provider_account_id,
        )
        oldest.provider_account_id = account_dto.provider_account_id
        await session.flush()


# ── BankAccount field set extracted from DTO ───────────────────────────────


def _dto_to_account_kwargs(dto: BankAccountDTO) -> dict:
    """Convert a BankAccount DTO into the kwargs dict for ORM column assignment."""
    return {
        # Identification
        "name": dto.name,
        "type": dto.type.value,
        "currency": dto.currency,
        "institution_name": dto.institution_name,
        # Identifiers
        "iban": dto.iban,
        "bic": dto.bic,
        "number": dto.number,
        # Balance & valuation
        "balance": dto.balance,
        "valuation": dto.valuation,
        "coming": dto.coming,
        "coming_balance": dto.coming_balance,
        "diff": dto.diff,
        "diff_percent": dto.diff_percent,
        "prev_diff": dto.prev_diff,
        "prev_diff_percent": dto.prev_diff_percent,
        # Context
        "usage": dto.usage,
        "ownership": dto.ownership,
        "company_name": dto.company_name,
        "opening_date": dto.opening_date,
        # State
        "bookmarked": dto.bookmarked,
        "display": dto.display,
        "powens_deleted_at": dto.powens_deleted_at,
        "powens_disabled_at": dto.powens_disabled_at,
        "powens_error": dto.powens_error,
        "powens_last_update": dto.powens_last_update,
        # Sync
        "last_synced_at": dto.last_synced_at,
        # JSONB raw payload
        "raw_data": dto.raw_data or {},
    }


# ── Public API ─────────────────────────────────────────────────────────────


async def list_accounts(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[BankAccount]:
    """All non-soft-deleted bank accounts of a user, sorted by name.

    Accounts flagged with `powens_deleted_at` (i.e. removed upstream in Powens)
    are excluded — the user sees the same view as in Powens. Auditors/admins
    needing the full set should query the table directly.
    """
    stmt = (
        select(BankAccount)
        .where(
            BankAccount.user_id == user_id,
            BankAccount.powens_deleted_at.is_(None),
        )
        .order_by(BankAccount.name)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def get_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> BankAccount | None:
    """Single non-soft-deleted bank account, filtered by user_id (multi-tenant safety).

    Returns None when the account was soft-deleted upstream — routes built on
    top of this naturally render 404, mirroring the user-visible view.
    """
    stmt = select(BankAccount).where(
        BankAccount.id == account_id,
        BankAccount.user_id == user_id,
        BankAccount.powens_deleted_at.is_(None),
    )
    res = await session.execute(stmt)
    return res.scalars().first()


async def upsert_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_dto: BankAccountDTO,
) -> BankAccount:
    """Insert or update based on (user_id, provider, provider_account_id).

    An account already known under another id (a bank connected again) is
    updated in place: its oldest row takes the new id first.

    If the DTO carries a `loan` sub-object, also upserts the Loan row
    transactionally (one-to-one with the BankAccount).
    """
    await _adopt_oldest_row(session, user_id, account_dto)
    stmt = select(BankAccount).where(
        BankAccount.user_id == user_id,
        BankAccount.provider == account_dto.provider,
        BankAccount.provider_account_id == account_dto.provider_account_id,
    )
    res = await session.execute(stmt)
    row = res.scalars().first()

    kwargs = _dto_to_account_kwargs(account_dto)

    if row is None:
        row = BankAccount(
            user_id=user_id,
            provider=account_dto.provider,
            provider_account_id=account_dto.provider_account_id,
            **kwargs,
        )
        session.add(row)
        await session.flush()  # so row.id is populated for the Loan FK
        logger.info(
            "Created bank_account user=%s provider=%s acc=%s",
            user_id,
            account_dto.provider,
            account_dto.provider_account_id,
        )
    else:
        for k, v in kwargs.items():
            setattr(row, k, v)

    # ── Nested Loan upsert (one-to-one) ────────────────────────────────────
    if account_dto.loan is not None:
        await _upsert_loan(session, user_id, row.id, account_dto.loan)

    await session.commit()
    await session.refresh(row)
    return row


async def _upsert_loan(
    session: AsyncSession,
    user_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    loan_dto,
) -> Loan:
    """Insert/update the Loan row attached to a BankAccount. Internal helper."""
    stmt = select(Loan).where(Loan.bank_account_id == bank_account_id)
    res = await session.execute(stmt)
    row = res.scalars().first()

    kwargs = {
        "total_amount": loan_dto.total_amount,
        "available_amount": loan_dto.available_amount,
        "used_amount": loan_dto.used_amount,
        "subscription_date": loan_dto.subscription_date,
        "maturity_date": loan_dto.maturity_date,
        "start_repayment_date": loan_dto.start_repayment_date,
        "deferred": loan_dto.deferred,
        "next_payment_amount": loan_dto.next_payment_amount,
        "next_payment_date": loan_dto.next_payment_date,
        "last_payment_amount": loan_dto.last_payment_amount,
        "last_payment_date": loan_dto.last_payment_date,
        "nb_payments_done": loan_dto.nb_payments_done,
        "nb_payments_left": loan_dto.nb_payments_left,
        "nb_payments_total": loan_dto.nb_payments_total,
        "rate": loan_dto.rate,
        "duration_months": loan_dto.duration_months,
        "insurance_label": loan_dto.insurance_label,
        "insurance_amount": loan_dto.insurance_amount,
        "insurance_rate": loan_dto.insurance_rate,
        "account_label": loan_dto.account_label,
        "loan_type": loan_dto.loan_type,
        "raw_data": loan_dto.raw_data or {},
    }

    if row is None:
        row = Loan(
            user_id=user_id,
            bank_account_id=bank_account_id,
            **kwargs,
        )
        session.add(row)
        logger.info("Created loan for bank_account=%s", bank_account_id)
    else:
        for k, v in kwargs.items():
            setattr(row, k, v)

    return row


async def delete_account(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> bool:
    """Delete a bank account + cascade Loan/holdings/transactions."""
    row = await get_account(session, user_id, account_id)
    if row is None:
        return False
    await session.delete(row)
    await session.commit()
    logger.info("Deleted bank_account=%s for user=%s", account_id, user_id)
    return True
