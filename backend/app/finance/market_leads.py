"""« Pistes de marché » : ratisser large chaque nuit, laisser le briefing trier (ADR-033).

Three sources of what people who commit money declare, none of them a
« signal » anyone typed by hand: bets on Polymarket that moved, insiders
buying their own company's shares on the open market, large funds opening
or closing a line in their 13F. Every observation above the thresholds in
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

from ..data import edgar, polymarket
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
    max_state_leads: int = Field(8, ge=0)


class InsiderRules(BaseModel):
    min_purchase_usd: float = Field(100_000, ge=0)
    big_purchase_usd: float = Field(1_000_000, ge=0)
    cluster_days: int = Field(30, ge=1)
    min_insiders: int = Field(2, ge=1)
    keep_days: int = Field(45, ge=1)


class Manager(BaseModel):
    name: str
    cik: int = Field(gt=0)


class FundRules(BaseModel):
    followed: list[Manager]
    min_position_usd: float = Field(100_000_000, ge=0)
    min_change_pct: float = Field(0.25, ge=0)
    max_leads_per_filing: int = Field(6, ge=0)
    keep_days: int = Field(21, ge=1)


class LeadsConfig(BaseModel):
    polymarket: PolymarketRules
    insiders: InsiderRules
    funds: FundRules


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


def _polymarket_leads(
    events: list[list[polymarket.Market]], rules: PolymarketRules, today: date
) -> list[MarketLead]:
    day = today.isoformat()
    out: list[MarketLead] = []
    for markets in events:
        for m in markets:
            if m.volume_24h_usd < rules.min_volume_24h_usd:
                continue
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
    ranked = sorted(
        (ms for ms in events if ms),
        key=lambda ms: -sum(m.volume_24h_usd for m in ms),
    )
    for markets in ranked[: rules.max_state_leads]:
        lead = max(markets, key=lambda m: m.yes_price)
        if lead.volume_24h_usd < rules.min_volume_24h_usd:
            continue
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
    """Read the last two index days, remember the purchases, return clusters and big buys.

    The state remembers which filings were already read (a filing is one
    request, a thousand a day) and the purchases kept, both pruned after
    `keep_days`.
    """
    seen: dict[str, str] = dict(state.get("seen") or {})
    purchases: list[dict[str, Any]] = list(state.get("purchases") or [])
    floor = (today - timedelta(days=rules.keep_days)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= floor}
    purchases = [p for p in purchases if (p.get("filed") or "") >= floor]

    for day in (today - timedelta(days=1), today):
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
