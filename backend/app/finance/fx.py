"""Amounts held in another currency, in euros at the ECB reference rate (ADR-038).

Tangent adds balances and spending up in euros. An account in SGD, USD or
HKD is counted at the latest reference rate the ECB publishes (one a working
day, about 30 currencies). When the ECB cannot be reached, the last rate this
process read still serves; a currency never read is left out of the totals,
not counted as if it were euros.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Iterable

from ..data import ecb
from ..errors import DataSourceError

logger = logging.getLogger(__name__)

EUR = "EUR"
_CODE = re.compile(r"[A-Z]{3}")
_LAST_KNOWN: dict[str, float] = {}  # units of the currency for one euro


def code(currency: str | None) -> str:
    """The ISO code an amount is held in; an account without one is in euros."""
    return (currency or EUR).strip().upper()


def eur_rate(currency: str) -> float | None:
    """Units of `currency` for one euro, as the ECB last published it."""
    ccy = code(currency)
    if ccy == EUR:
        return 1.0
    if not _CODE.fullmatch(ccy):
        return None
    try:
        rates = ecb.series(f"EXR/D.{ccy}.EUR.SP00.A", last_n=1)
        rate = float(rates.iloc[-1])
    except (DataSourceError, IndexError, ValueError) as exc:
        logger.warning(
            "Taux BCE %s indisponible (%s), dernier connu: %s", ccy, exc, _LAST_KNOWN.get(ccy)
        )
        return _LAST_KNOWN.get(ccy)
    if rate <= 0:
        return _LAST_KNOWN.get(ccy)
    _LAST_KNOWN[ccy] = rate
    return rate


async def to_eur_factors(currencies: Iterable[str | None]) -> dict[str, float]:
    """What an amount is multiplied by to read in euros, per currency.

    A currency without a rate is absent: its amounts are left out of totals.
    Euros alone never call the ECB.
    """
    factors = {EUR: 1.0}
    for ccy in sorted({code(c) for c in currencies} - {EUR}):
        rate = await asyncio.to_thread(eur_rate, ccy)
        if rate:
            factors[ccy] = 1.0 / rate
    return factors
