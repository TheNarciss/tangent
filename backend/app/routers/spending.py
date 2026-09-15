"""Spending — what leaves the current accounts, month by month and by category."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db import get_session
from ..finance import merchants
from ..repositories import bank_transactions as tx_repo

router = APIRouter(tags=["spending"])


class MonthSpending(BaseModel):
    month: str  # "2026-09"
    total: float  # € spent
    income: float = 0.0  # € received, own transfers left out
    by_category: dict[str, float]  # category → € spent; "autre" holds the unlabelled


class Merchant(BaseModel):
    name: str  # the bank's label, dates and amounts stripped
    total: float
    count: int


class CategorySpending(BaseModel):
    category: str
    total: float
    share: float  # of the window's total


class SpendingResponse(BaseModel):
    months: list[MonthSpending]  # oldest first, the current month last (partial)
    categories: list[CategorySpending]  # over the whole window, largest first
    merchants: list[Merchant]  # where the money went most, over the window
    monthly_average: float | None  # spending, over complete months only
    monthly_income_average: float | None  # income, over complete months only
    current_month_total: float
    unlabelled_share: float  # part of the window still without a category


@router.get("/spending", response_model=SpendingResponse)
async def read_spending(
    months: int = Query(6, ge=1, le=24, description="Window, in months, current one included"),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> SpendingResponse:
    """Debits on current accounts, per month and category.

    Transfers to savings, to investments and loan repayments are left out: the
    money left the account but was not spent. So is any transfer whose other
    leg lands on another of the user's own accounts. A transfer with no such
    leg counts, as « virement_sortant »: from here the money is simply gone.
    Uncategorised debits count under « autre », and the response says what
    share of the picture they are.
    """
    return await build_spending(session, user.id, months=months)


async def build_spending(
    session: AsyncSession, user_id: uuid.UUID, *, months: int = 6, today: date | None = None
) -> SpendingResponse:
    """The spending picture over the window; what the route serves and the archive keeps."""
    today = today or date.today()
    first = _shift(today.replace(day=1), -(months - 1))
    rows = await tx_repo.spending_by_month_and_category(session, user_id, since=first)
    credits = dict(
        (m.strftime("%Y-%m"), v)
        for m, v in await tx_repo.income_by_month(session, user_id, since=first)
    )
    labels = await tx_repo.spending_by_description(session, user_id, since=first)

    by_month: dict[str, dict[str, float]] = {}
    cursor = first
    while cursor <= today:
        by_month[cursor.strftime("%Y-%m")] = {}
        cursor = _shift(cursor, 1)
    by_category: dict[str, float] = {}
    unlabelled = 0.0
    for month_start, category, total in rows:
        key = month_start.strftime("%Y-%m")
        # A transfer still here has no other leg on an own account: the money
        # left — to a card account Tangent does not know, to someone.
        label = "virement_sortant" if category == "virement_interne" else (category or "autre")
        if category is None:
            unlabelled += total
        by_month.setdefault(key, {})
        by_month[key][label] = by_month[key].get(label, 0.0) + total
        by_category[label] = by_category.get(label, 0.0) + total

    month_list = [
        MonthSpending(
            month=key, total=sum(cats.values()), income=credits.get(key, 0.0), by_category=cats
        )
        for key, cats in sorted(by_month.items())
    ]
    complete = [m for m in month_list[:-1] if m.total > 0 or m.income > 0]
    grand_total = sum(by_category.values())
    return SpendingResponse(
        months=month_list,
        categories=[
            CategorySpending(category=c, total=t, share=t / grand_total if grand_total else 0.0)
            for c, t in sorted(by_category.items(), key=lambda kv: -kv[1])
        ],
        merchants=_merchants(labels),
        monthly_average=sum(m.total for m in complete) / len(complete) if complete else None,
        monthly_income_average=(
            sum(m.income for m in complete) / len(complete) if complete else None
        ),
        current_month_total=month_list[-1].total if month_list else 0.0,
        unlabelled_share=unlabelled / grand_total if grand_total else 0.0,
    )


def _shift(first_of_month: date, months: int) -> date:
    """The first day of the month `months` away (negative = back)."""
    index = first_of_month.year * 12 + first_of_month.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def _merchants(rows: list[tuple[str, float, int]], top: int = 10) -> list[Merchant]:
    """The bank's labels folded by merchant, largest first."""
    folded: dict[str, list[float]] = {}
    for label, total, count in rows:
        name = merchants.fold(label)
        agg = folded.setdefault(name, [0.0, 0.0])
        agg[0] += total
        agg[1] += count
    ranked = sorted(folded.items(), key=lambda kv: -kv[1][0])[:top]
    return [Merchant(name=name, total=t, count=int(n)) for name, (t, n) in ranked]
