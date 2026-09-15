"""Polymarket: what people who bet money expect, as probabilities.

The Gamma API serves every event and its markets without a key. An event
(« Fed decision in September? ») holds one market per outcome (« no
change », « cut by 25 bps »…); each market quotes a yes-price between 0 and
1, which reads as a probability, and how far it moved over a day, a week,
a month. Tags name the topic: `fed`, `economy`, `recession`, `oil`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from ..errors import DataSourceError
from . import http
from .config import config

logger = logging.getLogger(__name__)

_PAGE = 100  # the API's ceiling per call


@dataclass(frozen=True)
class Market:
    event_id: str
    event_title: str
    event_slug: str
    question: str
    yes_price: float  # probability of the first outcome, 0..1
    day_change: float  # in probability points (0.05 = five points)
    week_change: float
    volume_24h_usd: float
    end_date: str  # ISO, may be empty
    tags: tuple[str, ...]

    @property
    def url(self) -> str:
        return f"https://polymarket.com/event/{self.event_slug}"


def events(tag: str, *, ttl_hours: float = 1.0) -> list[dict[str, Any]]:
    """Every open event carrying the tag, most traded first."""
    cfg = config()
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        params = {
            "active": "true",
            "closed": "false",
            "tag_slug": tag,
            "order": "volume24hr",
            "ascending": "false",
            "limit": str(_PAGE),
            "offset": str(offset),
        }
        body = http.get_text(
            f"{cfg.polymarket.base_url}/events", params=params, ttl_hours=ttl_hours
        )
        page = _decode(body)
        out.extend(page)
        if len(page) < _PAGE:
            return out
        offset += _PAGE


def markets(event: dict[str, Any]) -> list[Market]:
    """The event's open markets, as far as the payload lets us read them."""
    tags = tuple(str(t.get("slug") or "") for t in event.get("tags") or [] if isinstance(t, dict))
    out: list[Market] = []
    for m in event.get("markets") or []:
        if not isinstance(m, dict) or m.get("closed"):
            continue
        prices = _list(m.get("outcomePrices"))
        if not prices:
            continue
        try:
            yes = float(prices[0])
        except (TypeError, ValueError):
            continue
        out.append(
            Market(
                event_id=str(event.get("id") or ""),
                event_title=str(event.get("title") or ""),
                event_slug=str(event.get("slug") or ""),
                question=str(m.get("question") or ""),
                yes_price=yes,
                day_change=_num(m.get("oneDayPriceChange")),
                week_change=_num(m.get("oneWeekPriceChange")),
                volume_24h_usd=_num(m.get("volume24hr")),
                end_date=str(m.get("endDate") or ""),
                tags=tags,
            )
        )
    return out


def _decode(body: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise DataSourceError(f"Réponse Polymarket illisible: {exc}") from exc
    if not isinstance(payload, list):
        raise DataSourceError("Réponse Polymarket inattendue (liste attendue).")
    return [e for e in payload if isinstance(e, dict)]


def _list(raw: Any) -> list[Any]:
    """`outcomePrices` arrives as a JSON string inside the JSON: '["0.12", "0.88"]'."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
        except ValueError:
            return []
        return decoded if isinstance(decoded, list) else []
    return []


def _num(raw: Any) -> float:
    try:
        return float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0
