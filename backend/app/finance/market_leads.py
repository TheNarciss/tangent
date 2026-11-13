"""« Pistes de marché » : ratisser large chaque nuit, laisser le briefing trier (ADR-033).

Sources of what people who commit money declare, none of them a « signal »
anyone typed by hand: bets on Polymarket and Kalshi that moved, insiders
buying their own company's shares on the open market, large funds opening
or closing a line in their 13F, known activists crossing 5 % of a company
in a 13D, futures speculators at a one-year extreme in the CFTC's weekly
count. Every observation above the thresholds in
`config/market_leads.yaml` becomes a lead, written to `data/market_leads.json`
with the raw numbers. Most of it is noise, on purpose: the morning briefing
reads the list and keeps zero to three, with the reason. Nothing here is a
buy or a sell.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from ..data import cftc, edgar, kalshi, polymarket
from ..errors import ConfigurationError, DataSourceError
from ..models import MarketLead, MarketLeadsResponse

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG = _ROOT / "config" / "market_leads.yaml"
_PATH = _ROOT / "data" / "market_leads.json"
_STATE = _ROOT / "data" / "market_leads_state.json"

_MEMORY: MarketLeadsResponse | None = None


# ── Rules ───────────────────────────────────────────────────────────────────


class PolymarketRules(BaseModel):
    tags: list[str]
    min_volume_24h_usd: float = Field(25_000, ge=0)
    min_week_move: float = Field(0.15, ge=0, le=1)
    min_days_to_resolution: int = Field(14, ge=0)
    max_state_leads: int = Field(8, ge=0)


class InsiderRules(BaseModel):
    min_purchase_usd: float = Field(100_000, ge=0)
    big_purchase_usd: float = Field(1_000_000, ge=0)
    cluster_days: int = Field(30, ge=1)
    min_insiders: int = Field(2, ge=1)
    keep_days: int = Field(45, ge=1)
    index_lookback_days: int = Field(4, ge=1)


class Manager(BaseModel):
    name: str
    cik: int = Field(gt=0)


class FundRules(BaseModel):
    followed: list[Manager]
    min_position_usd: float = Field(100_000_000, ge=0)
    min_change_pct: float = Field(0.25, ge=0)
    max_leads_per_filing: int = Field(6, ge=0)
    keep_days: int = Field(21, ge=1)


class ActivistRules(BaseModel):
    followed: list[Manager]
    keep_days: int = Field(30, ge=1)
    index_lookback_days: int = Field(4, ge=1)


class Contract(BaseModel):
    name: str  # as the CFTC writes it
    dataset: str = Field(pattern="^(financial|commodities)$")
    label: str


class PositioningRules(BaseModel):
    contracts: list[Contract]
    weeks: int = Field(52, ge=4)
    min_net_share: float = Field(0.05, ge=0, le=1)


class KalshiRules(BaseModel):
    series: list[str]
    min_volume_24h: float = Field(2_000, ge=0)
    min_week_move: float = Field(0.15, ge=0, le=1)
    min_days_to_resolution: int = Field(14, ge=0)
    max_state_leads: int = Field(6, ge=0)
    price_memory_days: int = Field(10, ge=8)


class LeadsConfig(BaseModel):
    polymarket: PolymarketRules
    insiders: InsiderRules
    funds: FundRules
    activists: ActivistRules
    positioning: PositioningRules
    kalshi: KalshiRules


@lru_cache(maxsize=1)
def config() -> LeadsConfig:
    if not _CONFIG.exists():
        raise ConfigurationError("market_leads.yaml introuvable.")
    try:
        return LeadsConfig.model_validate(yaml.safe_load(_CONFIG.read_text()) or {})
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError(f"market_leads.yaml malformé: {exc}") from exc


# ── Polymarket ──────────────────────────────────────────────────────────────


def polymarket_leads(rules: PolymarketRules, today: date) -> list[MarketLead]:
    """Bets that moved this week, and the state of the most traded ones."""
    seen: dict[str, list[polymarket.Market]] = {}
    for tag in rules.tags:
        try:
            events = polymarket.events(tag)
        except DataSourceError as exc:
            logger.warning("polymarket %s: %s", tag, exc)
            continue
        for event in events:
            markets = polymarket.markets(event)
            if markets and markets[0].event_id not in seen:
                seen[markets[0].event_id] = markets
    return _polymarket_leads(list(seen.values()), rules, today)


def _resolves_too_soon(m: polymarket.Market, rules: PolymarketRules, today: date) -> bool:
    """A bet settled within days (« Bitcoin above X on Friday? ») says nothing about a horizon."""
    if not m.end_date:
        return False
    try:
        end = date.fromisoformat(m.end_date[:10])
    except ValueError:
        return False
    return (end - today).days < rules.min_days_to_resolution


def _polymarket_leads(
    events: list[list[polymarket.Market]], rules: PolymarketRules, today: date
) -> list[MarketLead]:
    day = today.isoformat()
    kept: list[list[polymarket.Market]] = []
    for markets in events:
        markets = [
            m
            for m in markets
            if m.volume_24h_usd >= rules.min_volume_24h_usd
            and not _resolves_too_soon(m, rules, today)
        ]
        if markets:
            kept.append(markets)

    out: list[MarketLead] = []
    # One move per event, the largest: a price ladder (« will it reach 70, 80,
    # 90 k? ») moves on every rung at once and is still one piece of news.
    for markets in kept:
        m = max(markets, key=lambda m: abs(m.week_change))
        if abs(m.week_change) >= rules.min_week_move:
            out.append(
                MarketLead(
                    source="polymarket",
                    kind="prediction_move",
                    title=m.event_title,
                    detail=(
                        f"« {m.question} » : {m.yes_price:.0%} de oui, "
                        f"{m.week_change * 100:+.0f} points en une semaine, "
                        f"{m.volume_24h_usd:,.0f} $ échangés en 24 h"
                    ),
                    url=m.url,
                    observed_at=day,
                    weight=min(1.0, abs(m.week_change) / 0.5),
                )
            )
    # The state of expectations: the most traded events, their leading outcome.
    ranked = sorted(kept, key=lambda ms: -sum(m.volume_24h_usd for m in ms))
    for markets in ranked[: rules.max_state_leads]:
        lead = max(markets, key=lambda m: m.yes_price)
        out.append(
            MarketLead(
                source="polymarket",
                kind="prediction_state",
                title=lead.event_title,
                detail=(
                    f"Issue la plus probable : « {lead.question} » à {lead.yes_price:.0%}, "
                    f"{lead.week_change * 100:+.0f} points sur la semaine"
                ),
                url=lead.url,
                observed_at=day,
                weight=0.3,
            )
        )
    return out


# ── Insiders (Form 4) ───────────────────────────────────────────────────────


def _purchases_of(filing: edgar.Form4, rules: InsiderRules) -> list[dict[str, Any]]:
    """Open-market purchases by an officer or director, above the floor, one per owner."""
    insiders = [o for o in filing.owners if o.is_officer or o.is_director]
    if not insiders or not filing.symbol:
        return []
    amount = sum(t.shares * t.price for t in filing.transactions if t.code == "P" and t.acquired)
    if amount < rules.min_purchase_usd:
        return []
    days = [t.day for t in filing.transactions if t.code == "P" and t.day]
    owner = insiders[0]
    return [
        {
            "accession": filing.accession,
            "cik": filing.cik,
            "issuer": filing.issuer,
            "symbol": filing.symbol,
            "owner": owner.name,
            "title": owner.title or ("administrateur" if owner.is_director else "dirigeant"),
            "amount_usd": round(amount, 2),
            "day": min(days) if days else "",
        }
    ]


def insider_leads(
    rules: InsiderRules, state: dict[str, Any], today: date
) -> tuple[list[MarketLead], dict[str, Any]]:
    """Read the last index days, remember the purchases, return clusters and big buys.

    The SEC publishes a day's index around 02:00 UTC the next morning, after
    this job has run: a day is readable two nights later at the earliest, so
    the window looks back `index_lookback_days` and the state remembers which
    filings were already read (a filing is one request, a thousand a day).
    Purchases and the memory of filings are both pruned after `keep_days`.
    """
    seen: dict[str, str] = dict(state.get("seen") or {})
    purchases: list[dict[str, Any]] = list(state.get("purchases") or [])
    floor = (today - timedelta(days=rules.keep_days)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= floor}
    purchases = [p for p in purchases if (p.get("filed") or "") >= floor]

    for day in (today - timedelta(days=k) for k in range(rules.index_lookback_days, 0, -1)):
        try:
            entries = edgar.daily_index(day, "4")
        except DataSourceError as exc:
            logger.warning("edgar index %s: %s", day, exc)
            continue
        for entry in entries:
            if entry.accession in seen:
                continue
            seen[entry.accession] = entry.filed.isoformat()
            try:
                filing = edgar.form4(entry)
            except DataSourceError as exc:
                logger.info("form 4 %s: %s", entry.accession, exc)
                continue
            if filing is None:
                continue
            for p in _purchases_of(filing, rules):
                purchases.append({**p, "filed": entry.filed.isoformat()})

    return _insider_leads(purchases, rules, today), {"seen": seen, "purchases": purchases}


def _insider_leads(
    purchases: list[dict[str, Any]], rules: InsiderRules, today: date
) -> list[MarketLead]:
    day = today.isoformat()
    window = (today - timedelta(days=rules.cluster_days)).isoformat()
    by_issuer: dict[str, list[dict[str, Any]]] = {}
    for p in purchases:
        if (p.get("filed") or "") >= window:
            by_issuer.setdefault(p["symbol"], []).append(p)

    out: list[MarketLead] = []
    for symbol, rows in by_issuer.items():
        owners = {r["owner"] for r in rows}
        total = sum(r["amount_usd"] for r in rows)
        issuer = rows[0]["issuer"]
        url = (
            "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
            f"&CIK={rows[0]['cik']}&type=4&dateb=&owner=include&count=40"
        )
        if len(owners) >= rules.min_insiders:
            who = ", ".join(sorted({f"{r['owner']} ({r['title']})" for r in rows}))
            out.append(
                MarketLead(
                    source="edgar_form4",
                    kind="insider_cluster",
                    title=f"{issuer} ({symbol}) : {len(owners)} dirigeants achètent",
                    detail=f"{total:,.0f} $ d'achats en bourse en {rules.cluster_days} jours : {who}",
                    url=url,
                    observed_at=day,
                    symbols=[symbol],
                    weight=min(1.0, 0.6 + 0.1 * len(owners)),
                )
            )
            continue
        big = max(rows, key=lambda r: r["amount_usd"])
        if big["amount_usd"] >= rules.big_purchase_usd:
            out.append(
                MarketLead(
                    source="edgar_form4",
                    kind="insider_buy",
                    title=f"{issuer} ({symbol}) : un dirigeant achète gros",
                    detail=(
                        f"{big['owner']} ({big['title']}) achète pour "
                        f"{big['amount_usd']:,.0f} $ en bourse le {big['day'] or big['filed']}"
                    ),
                    url=url,
                    observed_at=day,
                    symbols=[symbol],
                    weight=0.5,
                )
            )
    return out


# ── Funds (13F-HR) ──────────────────────────────────────────────────────────


def fund_leads(
    rules: FundRules, state: dict[str, Any], today: date
) -> tuple[list[MarketLead], dict[str, Any]]:
    """What each followed manager changed in its latest 13F, kept `keep_days` after the filing."""
    out: list[MarketLead] = []
    new_state: dict[str, Any] = {}
    for manager in rules.followed:
        key = str(manager.cik)
        previous = state.get(key) or {}
        try:
            filings = edgar.filings_13f(manager.cik)
        except DataSourceError as exc:
            logger.warning("13F %s: %s", manager.name, exc)
            if previous:
                new_state[key] = previous
            continue
        if not filings:
            continue
        latest = filings[0]
        if previous.get("accession") == latest.accession:
            entry = previous
        else:
            try:
                now = edgar.holdings_13f(latest)
                before = edgar.holdings_13f(filings[1]) if len(filings) > 1 else {}
            except DataSourceError as exc:
                logger.warning("13F %s %s: %s", manager.name, latest.accession, exc)
                if previous:
                    new_state[key] = previous
                continue
            leads = _fund_diff(manager, latest, now, before, rules)
            entry = {
                "accession": latest.accession,
                "filed": latest.filed.isoformat(),
                "leads": [lead.model_dump() for lead in leads],
            }
        new_state[key] = entry
        if (today - date.fromisoformat(entry["filed"])).days <= rules.keep_days:
            out.extend(MarketLead.model_validate(lead) for lead in entry["leads"])
    return out, new_state


def _fund_diff(
    manager: Manager,
    filing: edgar.Filing13F,
    now: dict[str, edgar.Holding],
    before: dict[str, edgar.Holding],
    rules: FundRules,
) -> list[MarketLead]:
    day = filing.filed.isoformat()
    candidates: list[tuple[float, MarketLead]] = []
    for cusip, h in now.items():
        old = before.get(cusip)
        if old is None:
            if h.value_usd >= rules.min_position_usd:
                candidates.append(
                    (
                        h.value_usd,
                        MarketLead(
                            source="edgar_13f",
                            kind="fund_new_position",
                            title=f"{manager.name} : nouvelle ligne {h.name.title()}",
                            detail=(
                                f"{h.value_usd / 1e6:,.0f} M$ au {filing.period}, déposé le {day}"
                            ),
                            url=filing.folder + "/",
                            observed_at=day,
                            weight=0.7,
                        ),
                    )
                )
            continue
        if old.shares <= 0 or max(h.value_usd, old.value_usd) < rules.min_position_usd:
            continue
        change = h.shares / old.shares - 1.0
        if abs(change) >= rules.min_change_pct:
            candidates.append(
                (
                    max(h.value_usd, old.value_usd),
                    MarketLead(
                        source="edgar_13f",
                        kind="fund_change",
                        title=(
                            f"{manager.name} : {'renforce' if change > 0 else 'allège'} "
                            f"{h.name.title()}"
                        ),
                        detail=(
                            f"{change:+.0%} de titres, ligne de {h.value_usd / 1e6:,.0f} M$ "
                            f"au {filing.period}"
                        ),
                        url=filing.folder + "/",
                        observed_at=day,
                        weight=0.4,
                    ),
                )
            )
    for cusip, old in before.items():
        if cusip not in now and old.value_usd >= rules.min_position_usd:
            candidates.append(
                (
                    old.value_usd,
                    MarketLead(
                        source="edgar_13f",
                        kind="fund_exit",
                        title=f"{manager.name} : sort de {old.name.title()}",
                        detail=(
                            f"ligne de {old.value_usd / 1e6:,.0f} M$ soldée au {filing.period}"
                        ),
                        url=filing.folder + "/",
                        observed_at=day,
                        weight=0.6,
                    ),
                )
            )
    candidates.sort(key=lambda c: -c[0])
    return [lead for _, lead in candidates[: rules.max_leads_per_filing]]


# ── Activists (Schedule 13D) ────────────────────────────────────────────────


def activist_leads(
    rules: ActivistRules, state: dict[str, Any], today: date
) -> tuple[list[MarketLead], dict[str, Any]]:
    """Every initial 13D of the last days, kept when a followed activist is behind it.

    A handful of filings a day, most of them micro-caps nobody follows: the
    list of activists is the filter. The same index window as Form 4, the
    same memory of filings already read, leads kept `keep_days`.
    """
    seen: dict[str, str] = dict(state.get("seen") or {})
    kept: list[dict[str, Any]] = list(state.get("leads") or [])
    floor = (today - timedelta(days=rules.keep_days)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= floor}
    kept = [lead for lead in kept if (lead.get("observed_at") or "") >= floor]
    followed = {m.cik: m.name for m in rules.followed}

    for day in (today - timedelta(days=k) for k in range(rules.index_lookback_days, 0, -1)):
        try:
            entries = edgar.daily_index(day, "SCHEDULE 13D")
        except DataSourceError as exc:
            logger.warning("edgar index 13D %s: %s", day, exc)
            continue
        for entry in entries:
            # One filing, one row per co-filer: the accession is the key.
            if entry.accession in seen:
                continue
            seen[entry.accession] = entry.filed.isoformat()
            try:
                filing = edgar.schedule_13d(entry)
            except DataSourceError as exc:
                logger.info("schedule 13D %s: %s", entry.accession, exc)
                continue
            if filing is None:
                continue
            lead = _activist_lead(filing, followed, entry.filed)
            if lead is not None:
                kept.append(lead.model_dump())
    return [MarketLead.model_validate(lead) for lead in kept], {"seen": seen, "leads": kept}


def _activist_lead(
    filing: edgar.Schedule13D, followed: dict[int, str], filed: date
) -> MarketLead | None:
    persons = [p for p in filing.persons if p.cik in followed]
    if not persons or not filing.issuer:
        return None
    lead = max(persons, key=lambda p: p.percent)
    name = followed[lead.cik]
    return MarketLead(
        source="edgar_13d",
        kind="activist_stake",
        title=f"{name} : {lead.percent:.1f} % de {filing.issuer.title()}",
        detail=(
            f"Déclaration 13D déposée le {filed.isoformat()}, seuil franchi le "
            f"{filing.event_day or 'n/c'}, {lead.shares:,.0f} titres. Au-dessus de 5 %, "
            "un activiste doit dire ce qu'il compte faire."
        ),
        url=filing.folder + "/",
        observed_at=filed.isoformat(),
        weight=0.8,
    )


# ── Futures positioning (CFTC) ──────────────────────────────────────────────

_COT_URL = "https://publicreporting.cftc.gov/stories/s/Commitments-of-Traders/r4w3-av2u/"


def positioning_leads(rules: PositioningRules, today: date) -> list[MarketLead]:
    """Speculators at a one-year extreme, or changing side, contract by contract."""
    out: list[MarketLead] = []
    for contract in rules.contracts:
        try:
            weeks = cftc.positions(contract.dataset, contract.name, weeks=rules.weeks)
        except DataSourceError as exc:
            logger.warning("cftc %s: %s", contract.name, exc)
            continue
        lead = _positioning_lead(contract, weeks, rules)
        if lead is not None:
            out.append(lead)
    return out


def _positioning_lead(
    contract: Contract, weeks: list[cftc.Week], rules: PositioningRules
) -> MarketLead | None:
    if len(weeks) < 4:
        return None
    latest, previous = weeks[0], weeks[1]
    net, before = latest.net_share, previous.net_share
    history = [w.net_share for w in weeks[1:]]
    side = "acheteurs" if net > 0 else "vendeurs"
    detail = (
        f"Position nette des spéculateurs : {net:+.0%} de l'intérêt ouvert au {latest.day}, "
        f"contre {before:+.0%} la semaine d'avant ({'fonds à levier' if contract.dataset == 'financial' else 'gestion spéculative'}, CFTC)."
    )
    if abs(net) >= rules.min_net_share and (net >= max(history) or net <= min(history)):
        return MarketLead(
            source="cftc",
            kind="positioning_extreme",
            title=f"{contract.label} : les spéculateurs jamais aussi {side} depuis un an",
            detail=detail,
            url=_COT_URL,
            observed_at=latest.day,
            weight=0.5,
        )
    if net * before < 0 and abs(net) >= rules.min_net_share:
        return MarketLead(
            source="cftc",
            kind="positioning_flip",
            title=f"{contract.label} : les spéculateurs passent {side}",
            detail=detail,
            url=_COT_URL,
            observed_at=latest.day,
            weight=0.4,
        )
    return None


# ── Kalshi ──────────────────────────────────────────────────────────────────


def kalshi_leads(
    rules: KalshiRules, state: dict[str, Any], today: date
) -> tuple[list[MarketLead], dict[str, Any]]:
    """Bets that moved this week and the state of the most traded ones, with a price memory.

    Kalshi does not say how far a price moved, so the state keeps each
    market's price by day for `price_memory_days`; the move is against the
    price a week ago. The first week only has states to give.
    """
    prices: dict[str, dict[str, float]] = {
        t: dict(days) for t, days in (state.get("prices") or {}).items()
    }
    floor = (today - timedelta(days=rules.price_memory_days)).isoformat()
    day = today.isoformat()
    events: dict[str, list[kalshi.Market]] = {}
    for series in rules.series:
        try:
            found = kalshi.markets(series)
        except DataSourceError as exc:
            logger.warning("kalshi %s: %s", series, exc)
            continue
        for m in found:
            prices.setdefault(m.ticker, {})[day] = m.yes_price
            events.setdefault(m.event_ticker, []).append(m)
    prices = {
        t: {d: p for d, p in days.items() if d >= floor}
        for t, days in prices.items()
        if any(d >= floor for d in days)
    }
    return _kalshi_leads(list(events.values()), prices, rules, today), {"prices": prices}


def _week_ago(prices: dict[str, float], today: date) -> float | None:
    """The price recorded a week ago, or the latest one before that."""
    limit = (today - timedelta(days=7)).isoformat()
    earlier = [d for d in prices if d <= limit]
    return prices[max(earlier)] if earlier else None


def _kalshi_leads(
    events: list[list[kalshi.Market]],
    prices: dict[str, dict[str, float]],
    rules: KalshiRules,
    today: date,
) -> list[MarketLead]:
    day = today.isoformat()
    # An event is one question with several markets (hold, hike, cut…; or the
    # rungs of a ladder): traded or not as a whole, settled as a whole.
    kept: list[list[kalshi.Market]] = []
    for markets in events:
        markets = [
            m
            for m in markets
            if not _closes_too_soon(m.close_time, rules.min_days_to_resolution, today)
        ]
        if markets and sum(m.volume_24h for m in markets) >= rules.min_volume_24h:
            kept.append(markets)

    def move(m: kalshi.Market) -> float:
        old = _week_ago(prices.get(m.ticker, {}), today)
        return m.yes_price - old if old is not None else 0.0

    out: list[MarketLead] = []
    for markets in kept:
        m = max(markets, key=lambda m: abs(move(m)))
        delta = move(m)
        if abs(delta) >= rules.min_week_move:
            out.append(
                MarketLead(
                    source="kalshi",
                    kind="prediction_move",
                    title=m.title,
                    detail=(
                        f"{m.yes_price:.0%} de oui, {delta * 100:+.0f} points en une semaine, "
                        f"{m.volume_24h:,.0f} $ échangés en 24 h"
                    ),
                    url=m.url,
                    observed_at=day,
                    weight=min(1.0, abs(delta) / 0.5),
                )
            )
    ranked = sorted(kept, key=lambda ms: -sum(m.volume_24h for m in ms))
    for markets in ranked[: rules.max_state_leads]:
        # The market people actually trade: on a ladder of thresholds, the
        # contested rung; on a decision, the outcome in play. The highest
        # price would name the lowest rung, at 99 %, and say nothing.
        lead = max(markets, key=lambda m: m.volume_24h)
        delta = move(lead)
        out.append(
            MarketLead(
                source="kalshi",
                kind="prediction_state",
                title=lead.title,
                detail=(
                    f"Le marché le plus échangé de l'événement, à {lead.yes_price:.0%} de oui, "
                    f"{delta * 100:+.0f} points sur la semaine, "
                    f"{sum(m.volume_24h for m in markets):,.0f} $ échangés en 24 h sur l'événement"
                ),
                url=lead.url,
                observed_at=day,
                weight=0.3,
            )
        )
    return out


def _closes_too_soon(close_time: str, min_days: int, today: date) -> bool:
    if not close_time:
        return False
    try:
        return (date.fromisoformat(close_time[:10]) - today).days < min_days
    except ValueError:
        return False


# ── Store ───────────────────────────────────────────────────────────────────


def _load_state() -> dict[str, Any]:
    try:
        return dict(json.loads(_STATE.read_text()))
    except (OSError, ValueError):
        return {}


def refresh(today: date | None = None) -> MarketLeadsResponse:
    """Read every source, write the leads and the state. One source down costs its leads only."""
    global _MEMORY
    cfg = config()
    today = today or date.today()
    state = _load_state()
    leads: list[MarketLead] = []

    try:
        leads.extend(polymarket_leads(cfg.polymarket, today))
    except Exception:
        logger.exception("pistes: Polymarket hors de portée")
    try:
        found, state["insiders"] = insider_leads(cfg.insiders, state.get("insiders") or {}, today)
        leads.extend(found)
    except Exception:
        logger.exception("pistes: EDGAR Form 4 hors de portée")
    try:
        found, state["funds"] = fund_leads(cfg.funds, state.get("funds") or {}, today)
        leads.extend(found)
    except Exception:
        logger.exception("pistes: EDGAR 13F hors de portée")
    try:
        found, state["activists"] = activist_leads(
            cfg.activists, state.get("activists") or {}, today
        )
        leads.extend(found)
    except Exception:
        logger.exception("pistes: EDGAR 13D hors de portée")
    try:
        leads.extend(positioning_leads(cfg.positioning, today))
    except Exception:
        logger.exception("pistes: CFTC hors de portée")
    try:
        found, state["kalshi"] = kalshi_leads(cfg.kalshi, state.get("kalshi") or {}, today)
        leads.extend(found)
    except Exception:
        logger.exception("pistes: Kalshi hors de portée")

    leads.sort(key=lambda lead: -lead.weight)
    out = MarketLeadsResponse(
        computed_at=datetime.now(UTC).isoformat(timespec="seconds"), leads=leads
    )
    _MEMORY = out
    try:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        _STATE.write_text(json.dumps(state))
        _PATH.write_text(out.model_dump_json())
        logger.info("pistes: %d pistes écrites dans %s", len(leads), _PATH)
    except OSError as exc:
        logger.error("pistes: %s inaccessible en écriture (%s), gardées en mémoire", _PATH, exc)
    return out


def load() -> MarketLeadsResponse | None:
    """The leads as last collected: the file, else what this process computed."""
    try:
        return MarketLeadsResponse.model_validate_json(_PATH.read_text())
    except (OSError, ValueError):
        return _MEMORY
