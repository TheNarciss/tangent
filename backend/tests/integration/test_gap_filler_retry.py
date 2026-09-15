"""A row the LLM looked at is not sent again: in flight, or nothing found (ADR-021)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.aggregator import AccountType, Transaction
from app.aggregator import BankAccount as BankAccountDTO
from app.db.engine import async_session_factory
from app.db.models import BankAccount, BankTransaction
from app.finance.gap_filler import engine
from app.finance.gap_filler.fields.transaction_category import FIELD_CATEGORY
from app.repositories import bank_accounts as accounts_repo
from app.repositories import bank_transactions as txs_repo


async def _user(client, email: str) -> uuid.UUID:
    from app.auth.models import User

    client.cookies.clear()
    resp = await client.post(
        "/api/auth/register", json={"email": email, "password": "TestPwd123!", "display_name": "g"}
    )
    assert resp.status_code in (200, 201), resp.text
    client.cookies.clear()
    async with async_session_factory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalars().first()
        assert user is not None
        return user.id


async def _gaps_for(user_id: uuid.UUID) -> list[uuid.UUID]:
    async with async_session_factory() as session:
        gaps = await engine.collect_gaps(session, user_id=user_id, fields=[FIELD_CATEGORY])
        return sorted(g.row_id for g in gaps)


@pytest.mark.integration
async def test_rows_sent_or_answered_empty_wait_before_being_asked_again(client):
    run_id = uuid.uuid4().hex[:8]
    user_id = await _user(client, f"gapretry-{run_id}@test.com")
    try:
        async with async_session_factory() as session:
            acc = await accounts_repo.upsert_account(
                session,
                user_id,
                BankAccountDTO(
                    provider="powens",
                    provider_account_id=f"acc-{run_id}",
                    name="Courant",
                    type=AccountType.CHECKING,
                    currency="EUR",
                    balance=100.0,
                ),
            )
            await txs_repo.upsert_transactions(
                session,
                user_id,
                acc.id,
                [
                    Transaction(
                        provider="powens",
                        provider_transaction_id=f"t{i}-{run_id}",
                        provider_account_id=f"acc-{run_id}",
                        amount=-10.0,
                        currency="EUR",
                        transaction_date=date(2026, 9, 1),
                        description=f"MARCHAND {i}",
                    )
                    for i in range(3)
                ],
            )
            await session.commit()

        before = await _gaps_for(user_id)
        assert len(before) == 3

        # Sent to the LLM: stamped, and out of the next collection.
        async with async_session_factory() as session:
            gaps = await engine.collect_gaps(session, user_id=user_id, fields=[FIELD_CATEGORY])
            await engine.mark_submitted(session, gaps[:2])
            await session.commit()
        assert await _gaps_for(user_id) == before[2:]

        # A month later the answer never came, or came back empty: asked once more.
        async with async_session_factory() as session:
            await session.execute(
                update(BankTransaction)
                .where(BankTransaction.user_id == user_id)
                .values(
                    category_resolved_at=datetime.now(UTC)
                    - timedelta(days=engine.RETRY_AFTER_DAYS + 1)
                )
            )
            await session.commit()
        assert await _gaps_for(user_id) == before

        # A batched answer writes only the rows named, and only while still empty.
        a, b, c = before
        async with async_session_factory() as session:
            ok = await engine._apply_batched(
                session,
                FIELD_CATEGORY,
                {
                    "items": [
                        {"id": str(a), "category": "alimentation"},
                        {"id": str(b), "category": "transport"},
                        {"id": str(uuid.uuid4()), "category": "loisirs"},
                    ]
                },
            )
            await session.commit()
        assert ok is True
        async with async_session_factory() as session:
            rows = (
                await session.execute(
                    select(
                        BankTransaction.id,
                        BankTransaction.category,
                        BankTransaction.category_source,
                    ).where(BankTransaction.user_id == user_id)
                )
            ).all()
        got = {row_id: (cat, src) for row_id, cat, src in rows}
        assert got[a] == ("alimentation", "llm")
        assert got[b] == ("transport", "llm")
        assert got[c] == (None, None)
        assert await _gaps_for(user_id) == [c]
    finally:
        async with async_session_factory() as session:
            await session.execute(
                BankAccount.__table__.delete().where(BankAccount.user_id == user_id)
            )
            await session.commit()
