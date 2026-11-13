"""A bank connected again: same accounts, same history, no duplicate.

Powens numbers accounts and transactions per connection. Re-adding a bank
whose connection broke used to show every account twice, the old one frozen.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app.aggregator import AccountType, SyncResult, Transaction
from app.aggregator import BankAccount as BankAccountDTO
from app.aggregator.persist import persist_sync_result
from app.auth.models import User
from app.db.engine import async_session_factory
from app.db.models import BankAccount, BankTransaction
from app.repositories import bank_transactions as txs_repo

IBAN = "FR7610207000012345678901234"


async def _user(client) -> uuid.UUID:
    email = f"reconnect-{secrets.token_hex(4)}@test.com"
    client.cookies.clear()
    resp = await client.post("/api/auth/register", json={"email": email, "password": "TestPwd123!"})
    assert resp.status_code in (200, 201), resp.text
    client.cookies.clear()
    async with async_session_factory() as session:
        return (await session.execute(select(User.id).where(User.email == email))).scalar_one()


def _account(pid: str, connection: int, day: int) -> BankAccountDTO:
    return BankAccountDTO(
        provider="powens",
        provider_account_id=pid,
        name="Compte courant",
        type=AccountType.CHECKING,
        currency="EUR",
        institution_name="Banque Populaire",
        iban=IBAN if connection == 10 else " ".join(IBAN[i : i + 4] for i in range(0, 27, 4)),
        balance=float(day),
        powens_last_update=datetime(2026, 10, day, 8, tzinfo=UTC),
        raw_data={"id": int(pid), "id_connection": connection},
    )


def _card(pid: str, connection: int, day: int) -> BankAccountDTO:
    return BankAccountDTO(
        provider="powens",
        provider_account_id=pid,
        name="Carte",
        type=AccountType.CARD,
        currency="EUR",
        institution_name="Banque Populaire",
        number="4974XXXXXXXX1234",
        balance=0.0,
        powens_last_update=datetime(2026, 10, day, 8, tzinfo=UTC),
        raw_data={"id": int(pid), "id_connection": connection},
    )


def _tx(tid: str, pid: str, day: int, amount: float, label: str) -> Transaction:
    return Transaction(
        provider="powens",
        provider_transaction_id=tid,
        provider_account_id=pid,
        amount=amount,
        currency="EUR",
        transaction_date=date(2026, 10, day),
        description=label,
    )


def _sync(accounts: list[BankAccountDTO], transactions: list[Transaction]) -> SyncResult:
    return SyncResult(
        success=True,
        provider="powens",
        accounts=accounts,
        transactions=transactions,
        synced_at=datetime.now(UTC),
    )


async def _state(user_id: uuid.UUID) -> tuple[list[BankAccount], list[tuple]]:
    async with async_session_factory() as session:
        accounts = list(
            (
                await session.execute(
                    select(BankAccount)
                    .where(BankAccount.user_id == user_id)
                    .order_by(BankAccount.created_at)
                )
            ).scalars()
        )
        txs = (
            await session.execute(
                select(
                    BankTransaction.bank_account_id,
                    BankTransaction.provider_transaction_id,
                    BankTransaction.description,
                    BankTransaction.category,
                )
                .where(BankTransaction.user_id == user_id)
                .order_by(BankTransaction.provider_transaction_id)
            )
        ).all()
    return accounts, [tuple(t) for t in txs]


async def _cleanup(user_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(BankAccount.__table__.delete().where(BankAccount.user_id == user_id))
        await session.commit()


@pytest.mark.integration
async def test_a_bank_connected_again_keeps_its_accounts_and_their_history(client):
    user_id = await _user(client)
    old_history = [
        _tx("a1", "101", 4, -5.18, "STARBUCKS"),
        _tx("a2", "101", 4, -5.18, "STARBUCKS"),
        _tx("a3", "101", 5, -42.0, "CARREFOUR"),
    ]
    try:
        async with async_session_factory() as session:
            await persist_sync_result(
                session, user_id, _sync([_account("101", 10, 8), _card("102", 10, 8)], old_history)
            )
        accounts, txs = await _state(user_id)
        checking = next(a for a in accounts if a.type == "checking")
        carrefour = next(t for t in txs if t[1] == "a3")
        async with async_session_factory() as session:
            row = (
                await session.execute(
                    select(BankTransaction.id).where(
                        BankTransaction.bank_account_id == checking.id,
                        BankTransaction.provider_transaction_id == carrefour[1],
                    )
                )
            ).scalar_one()
            await txs_repo.update_category(session, user_id, row, "alimentation")
            await session.commit()

        # The connection broke; the bank is added again. Powens lists both.
        new_history = [
            _tx("b1", "201", 4, -5.18, "STARBUCKS"),
            _tx("b2", "201", 4, -5.18, "STARBUCKS"),
            _tx("b3", "201", 5, -42.0, "CARREFOUR"),
            _tx("b4", "201", 9, -7.62, "KOPITIAM"),
        ]
        both = _sync(
            [
                _account("101", 10, 8),
                _card("102", 10, 8),
                _account("201", 20, 10),
                _card("202", 20, 10),
            ],
            old_history + new_history,
        )
        for _ in range(2):  # and again: nothing moves the second time
            async with async_session_factory() as session:
                await persist_sync_result(session, user_id, both)

            accounts, txs = await _state(user_id)
            assert sorted(a.provider_account_id for a in accounts) == ["201", "202"]
            again = next(a for a in accounts if a.type == "checking")
            assert again.id == checking.id
            assert again.balance == 10.0
            assert again.raw_data["id_connection"] == 20
            assert txs == [
                (checking.id, "b1", "STARBUCKS", None),
                (checking.id, "b2", "STARBUCKS", None),
                (checking.id, "b3", "CARREFOUR", "alimentation"),
                (checking.id, "b4", "KOPITIAM", None),
            ]
    finally:
        await _cleanup(user_id)


@pytest.mark.integration
async def test_a_duplicate_made_before_the_fix_folds_into_the_oldest_row(client):
    user_id = await _user(client)
    try:
        async with async_session_factory() as session:
            await persist_sync_result(
                session,
                user_id,
                _sync([_account("101", 10, 8)], [_tx("a1", "101", 4, -5.18, "STARBUCKS")]),
            )
            # What the old code did on the first sync of the new connection.
            duplicate = BankAccount(
                user_id=user_id,
                provider="powens",
                provider_account_id="201",
                name="Compte courant",
                type="checking",
                currency="EUR",
                institution_name="Banque Populaire",
                iban=IBAN,
                balance=9.0,
                raw_data={"id": 201, "id_connection": 20},
            )
            session.add(duplicate)
            await session.flush()
            session.add(
                BankTransaction(
                    user_id=user_id,
                    bank_account_id=duplicate.id,
                    provider_transaction_id="b1",
                    amount=-5.18,
                    currency="EUR",
                    transaction_date=date(2026, 10, 4),
                    description="STARBUCKS",
                )
            )
            await session.commit()
        accounts, _ = await _state(user_id)
        oldest = accounts[0]
        assert len(accounts) == 2

        async with async_session_factory() as session:
            await persist_sync_result(
                session,
                user_id,
                _sync(
                    [_account("101", 10, 8), _account("201", 20, 10)],
                    [
                        _tx("b1", "201", 4, -5.18, "STARBUCKS"),
                        _tx("b5", "201", 9, -7.62, "KOPITIAM"),
                    ],
                ),
            )

        accounts, txs = await _state(user_id)
        assert [(a.id, a.provider_account_id) for a in accounts] == [(oldest.id, "201")]
        assert txs == [
            (oldest.id, "b1", "STARBUCKS", None),
            (oldest.id, "b5", "KOPITIAM", None),
        ]
    finally:
        await _cleanup(user_id)
