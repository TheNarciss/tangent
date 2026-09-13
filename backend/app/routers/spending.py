"""Spending — what leaves the current accounts, month by month and by category."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db import get_session
from ..repositories import bank_transactions as tx_repo

router = APIRouter(tags=["spending"])


class MonthSpending(BaseModel):
    month: str  # "2026-09"
    total: float
    by_category: dict[str, float]  # category → € spent; "autre" holds the unlabelled


class CategorySpending(BaseModel):
    category: str
    total: float
    share: float  # of the window's total


class SpendingResponse(BaseModel):
    months: list[MonthSpending]  # oldest first, the current month last (partial)
    categories: list[CategorySpending]  # over the whole window, largest first
    monthly_average: float | None  # over complete months only
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
    money left the account but was not spent. Uncategorised debits count under
    « autre », and the response says what share of the picture they are, so a
    freshly synced account does not pass for a well-labelled one.
    """
    today = date.today()
    first = _shift(today.replace(day=1), -(months - 1))
    rows = await tx_repo.spending_by_month_and_category(session, user.id, since=first)

    by_month: dict[str, dict[str, float]] = {}
    cursor = first
    while cursor <= today:
        by_month[cursor.strftime("%Y-%m")] = {}
        cursor = _shift(cursor, 1)
    by_category: dict[str, float] = {}
    unlabelled = 0.0
    for month_start, category, total in rows:
        key = month_start.strftime("%Y-%m")
        label = category or "autre"
        if category is None:
            unlabelled += total
        by_month.setdefault(key, {})
        by_month[key][label] = by_month[key].get(label, 0.0) + total
        by_category[label] = by_category.get(label, 0.0) + total

    month_list = [
        MonthSpending(month=key, total=sum(cats.values()), by_category=cats)
        for key, cats in sorted(by_month.items())
    ]
    complete = [m.total for m in month_list[:-1] if m.total > 0]
    grand_total = sum(by_category.values())
    return SpendingResponse(
        months=month_list,
        categories=[
            CategorySpending(category=c, total=t, share=t / grand_total if grand_total else 0.0)
            for c, t in sorted(by_category.items(), key=lambda kv: -kv[1])
        ],
        monthly_average=sum(complete) / len(complete) if complete else None,
        current_month_total=month_list[-1].total if month_list else 0.0,
        unlabelled_share=unlabelled / grand_total if grand_total else 0.0,
    )


def _shift(first_of_month: date, months: int) -> date:
    """The first day of the month `months` away (negative = back)."""
    index = first_of_month.year * 12 + first_of_month.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)
