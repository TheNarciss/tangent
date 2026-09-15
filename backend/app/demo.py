"""A demonstration account with believable data, for Apple's reviewers and for demos (ADR-035).

The reviewer cannot connect a bank. This gives them a person: a current
account with three months of everyday spending, a Livret A, a PEA with two
index funds bought monthly, and sixty days of portfolio readings. The data
goes through the same door as a real synchronisation (`persist_sync_result`),
so every screen sees exactly what it would see for anyone.

    DEMO_EMAIL=demo@example.com DEMO_PASSWORD=… python -m app.demo

Running it again refreshes the same account: same e-mail, new password,
data replaced. The provider is `demo`; nothing here reaches a bank.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi_users.exceptions import UserAlreadyExists, UserNotExists
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from .aggregator.persist import persist_sync_result
from .aggregator.types import AccountType, BankAccount, Investment, SyncResult, Transaction
from .auth import User, UserCreate
from .auth.manager import UserManager, _password_helper
from .auth.oauth_models import OAuthAccount
from .auth.terms_version import CURRENT_TERMS_VERSION
from .repositories import snapshots as snapshots_repo

logger = logging.getLogger(__name__)

PROVIDER = "demo"
BANK = "Banque Démo"

CHECKING, LIVRET, PEA = "demo-checking", "demo-livret", "demo-pea"
WORLD, SP500 = "CW8.PA", "PE500.PA"

# Prices used for the seeded readings only; the screens fetch the live ones.
_WORLD_PRICE, _SP500_PRICE = 520.0, 42.0
_WORLD_QTY, _SP500_QTY = 12.0, 60.0


def _month_shift(day: date, months: int) -> date:
    y, m = divmod(day.month - 1 + months, 12)
    return date(day.year + y, m + 1, min(day.day, 28))


def accounts(today: date) -> list[BankAccount]:
    pea_value = _WORLD_QTY * _WORLD_PRICE + _SP500_QTY * _SP500_PRICE
    stamp = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    common = {
        "provider": PROVIDER,
        "currency": "EUR",
        "institution_name": BANK,
        "last_synced_at": stamp,
    }
    return [
        BankAccount(
            provider_account_id=CHECKING,
            name="Compte courant",
            type=AccountType.CHECKING,
            balance=2340.55,
            **common,
        ),
        BankAccount(
            provider_account_id=LIVRET,
            name="Livret A",
            type=AccountType.LIVRET_A,
            balance=8500.0,
            **common,
        ),
        BankAccount(
            provider_account_id=PEA,
            name="PEA",
            type=AccountType.PEA,
            balance=pea_value,
            valuation=pea_value,
            **common,
        ),
    ]


def investments() -> list[Investment]:
    return [
        Investment(
            provider=PROVIDER,
            provider_investment_id="demo-inv-world",
            provider_account_id=PEA,
            ticker=WORLD,
            isin="LU1681043599",
            label="Amundi MSCI World UCITS ETF",
            quantity=_WORLD_QTY,
            unit_price=455.0,
            current_value=_WORLD_QTY * _WORLD_PRICE,
            currency="EUR",
        ),
        Investment(
            provider=PROVIDER,
            provider_investment_id="demo-inv-sp500",
            provider_account_id=PEA,
            ticker=SP500,
            isin="FR0011550185",
            label="Amundi PEA S&P 500 UCITS ETF",
            quantity=_SP500_QTY,
            unit_price=36.5,
            current_value=_SP500_QTY * _SP500_PRICE,
            currency="EUR",
        ),
    ]


def transactions(today: date) -> list[Transaction]:
    """Three months of an ordinary life: salary, rent, groceries, a few pleasures, monthly savings."""
    rows: list[
        tuple[date, str, float, str, str]
    ] = []  # (day, account, amount, description, category)
    first = _month_shift(today.replace(day=1), -2)
    for k in range(3):
        month = _month_shift(first, k)
        rows += [
            (month.replace(day=2), CHECKING, 2450.0, "VIR SALAIRE ATELIER NORD", "salaire"),
            (month.replace(day=3), CHECKING, -850.0, "PRLV LOYER RESIDENCE DES LILAS", "loyer"),
            (
                month.replace(day=5),
                CHECKING,
                -300.0,
                "VIR PEA VERSEMENT MENSUEL",
                "epargne_investissement",
            ),
            (month.replace(day=5), PEA, 300.0, "VERSEMENT MENSUEL", "epargne_investissement"),
            (month.replace(day=6), CHECKING, -100.0, "VIR LIVRET A", "virement_interne"),
            (
                month.replace(day=6),
                LIVRET,
                100.0,
                "VIREMENT DEPUIS COMPTE COURANT",
                "virement_interne",
            ),
            (month.replace(day=8), CHECKING, -34.99, "PRLV FREE MOBILE", "telecom_internet"),
            (month.replace(day=9), CHECKING, -13.49, "PRLV NETFLIX", "abonnements"),
            (month.replace(day=10), CHECKING, -62.0, "PRLV MAIF ASSURANCE", "assurance"),
            (month.replace(day=12), CHECKING, -49.0, "SNCF CONNECT", "transport"),
            (month.replace(day=15), CHECKING, -28.5, "CB LE PETIT BISTROT", "restaurant"),
            (month.replace(day=18), CHECKING, -75.0, "CB DECATHLON", "shopping"),
            (month.replace(day=22), CHECKING, -24.0, "CB PHARMACIE CENTRALE", "sante"),
            (month.replace(day=26), CHECKING, -41.0, "CB CINEMA PATHE", "loisirs"),
        ]
        for week in range(4):
            day = month.replace(day=min(4 + 7 * week, 28))
            rows.append((day, CHECKING, -68.4 - 3 * week, "CB CARREFOUR MARKET", "alimentation"))
    out: list[Transaction] = []
    for i, (day, account, amount, description, category) in enumerate(rows):
        if day > today:
            continue
        out.append(
            Transaction(
                provider=PROVIDER,
                provider_transaction_id=f"demo-tx-{i:03d}",
                provider_account_id=account,
                amount=amount,
                currency="EUR",
                transaction_date=day,
                description=description,
                category=category,
                category_source="api",
            )
        )
    return out


async def _user(session: AsyncSession, email: str, password: str) -> User:
    """The demo person, created or refreshed, terms accepted, e-mail verified."""
    manager = UserManager(
        SQLAlchemyUserDatabase(session, User, OAuthAccount),  # type: ignore[type-var]
        password_helper=_password_helper,
    )
    try:
        user = await manager.get_by_email(email)
        user.hashed_password = _password_helper.hash(password)
    except UserNotExists:
        try:
            user = await manager.create(
                UserCreate(email=email, password=password, display_name="Démo", is_verified=True)
            )
        except UserAlreadyExists:  # pragma: no cover — raced by another seed
            user = await manager.get_by_email(email)
    user.is_verified = True
    user.terms_version_accepted = CURRENT_TERMS_VERSION
    user.terms_accepted_at = datetime.now(UTC)
    await session.flush()
    return user


async def seed(
    session: AsyncSession, *, email: str, password: str, today: date | None = None
) -> uuid.UUID:
    """Create or refresh the demo account and everything it holds. Commits."""
    today = today or date.today()
    user = await _user(session, email, password)
    result = SyncResult(
        success=True,
        provider=PROVIDER,
        accounts=accounts(today),
        investments=investments(),
        transactions=transactions(today),
        synced_at=datetime.now(UTC),
    )
    await persist_sync_result(session, user.id, result)

    # Sixty days of readings: a gentle rise, one contribution a month, so that
    # performance, drawdown and « depuis hier » have something to say.
    quantities = {WORLD: _WORLD_QTY, SP500: _SP500_QTY}
    base = _WORLD_QTY * _WORLD_PRICE + _SP500_QTY * _SP500_PRICE
    for back in range(60, -1, -1):
        day = today - timedelta(days=back)
        wobble = 1 + 0.04 * ((back * 7) % 11 - 5) / 10 - 0.0008 * back
        flow = 300.0 if day.day == 5 and back > 0 else 0.0
        await snapshots_repo.record_snapshot(
            session,
            user.id,
            snapshot_date=day,
            total_value=round(base * wobble, 2),
            quantities=quantities,
            net_flow=flow,
        )
    await session.commit()
    logger.info("demo: compte %s prêt (%s)", email, user.id)
    return user.id


async def _main() -> int:
    from .db import async_session_factory

    email = os.getenv("DEMO_EMAIL", "").strip()
    password = os.getenv("DEMO_PASSWORD", "")
    if not email or len(password) < 8:
        print(
            "DEMO_EMAIL et DEMO_PASSWORD (8 caractères au moins) sont attendus dans l'environnement."
        )
        return 2
    async with async_session_factory() as session:
        user_id = await seed(session, email=email, password=password)
    print(f"Compte de démonstration prêt : {email} ({user_id})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
