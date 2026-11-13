"""One line's own price — what opens when a position is tapped, and the « Cours » tab."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool

from ..auth import User, current_active_user
from ..errors import TickerNotFoundError
from ..finance import classification, market
from ..models import QuoteHistoryResponse, QuoteMatch

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("/search", response_model=list[QuoteMatch])
async def search_quotes(
    q: str = Query(min_length=1, max_length=80),
    user: User = Depends(current_active_user),
) -> list[QuoteMatch]:
    """Instruments whose name or symbol matches. Empty rather than failing."""
    matches = await run_in_threadpool(market.search, q)
    return [QuoteMatch(**asdict(m)) for m in matches]


@router.get("/history", response_model=QuoteHistoryResponse)
async def read_history(
    symbol: str = Query(min_length=1, max_length=40),
    scale: str = Query("1y", pattern="^(1d|1w|1m|6m|1y|5y|max)$"),
    isin: str | None = Query(None, max_length=12),
    user: User = Depends(current_active_user),
) -> QuoteHistoryResponse:
    """The closes of one symbol at one scale.

    `isin` is the fallback for a bank line whose ticker Yahoo does not know:
    OpenFIGI names the venue the ISIN trades on, and that symbol is read
    instead. 422 when neither is quoted anywhere we read.
    """
    return QuoteHistoryResponse(**asdict(await run_in_threadpool(_history, symbol, scale, isin)))


def _history(symbol: str, scale: str, isin: str | None) -> market.History:
    try:
        return market.history(symbol, scale)
    except TickerNotFoundError:
        quote = classification.quotes([isin]).get(isin) if isin else None
        if quote is None or quote.ticker == symbol:
            raise
        return market.history(quote.ticker, scale)
