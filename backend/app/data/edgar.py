"""SEC EDGAR: what insiders and large funds declare, read from the filings.

Two forms, public and keyless. Form 4: an officer, director or 10 % holder
bought or sold shares of their own company, filed within two business days.
13F-HR: a manager above 100 M$ lists its US holdings, 45 days after each
quarter. The daily index names every filing of a day by form type; a filing
is one document, fetched on its own. The SEC asks for an identified
User-Agent and at most ten requests a second: `_paced` keeps under it.

The XML inside a filing follows a fixed schema written by machines, so the
few fields we need are cut out with patterns rather than an XML parser: no
entity, no namespace, nothing to resolve.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import date

from ..errors import DataSourceError
from . import http
from .config import config

logger = logging.getLogger(__name__)

_LAST_CALL = 0.0


def _paced() -> None:
    """Sleep so that two EDGAR calls stay `min_seconds_between_requests` apart."""
    global _LAST_CALL
    gap = config().edgar.min_seconds_between_requests
    wait = _LAST_CALL + gap - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _LAST_CALL = time.monotonic()


def _get(url: str, *, ttl_hours: float, cache: bool = True) -> str:
    _paced()
    return http.get_text(url, ttl_hours=ttl_hours, cache=cache)


# ── Daily index ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class IndexEntry:
    form: str
    company: str
    cik: int
    filed: date
    path: str  # relative to the archives root: edgar/data/<cik>/<accession>.txt

    @property
    def accession(self) -> str:
        return self.path.rsplit("/", 1)[-1].removesuffix(".txt")


def daily_index(day: date, form: str) -> list[IndexEntry]:
    """Every filing of that form type on that day. Empty on a day without index (weekend)."""
    cfg = config().edgar
    quarter = (day.month - 1) // 3 + 1
    url = f"{cfg.archives_url}/edgar/daily-index/{day.year}/QTR{quarter}/form.{day:%Y%m%d}.idx"
    try:
        body = _get(url, ttl_hours=24)
    except DataSourceError as exc:
        # No index for a weekend, and none yet for a day the SEC has not
        # closed: it answers 403, not 404, and publishes a day's index around
        # 02:00 UTC the next morning.
        if "404" in str(exc) or "403" in str(exc):
            return []
        raise
    return parse_index(body, form)


def parse_index(body: str, form: str) -> list[IndexEntry]:
    """Lines of `form.YYYYMMDD.idx`: form type, company, CIK, date, file name — space-aligned."""
    out: list[IndexEntry] = []
    for line in body.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0] != form:
            continue
        path, filed, cik = parts[-1], parts[-2], parts[-3]
        if not (cik.isdigit() and filed.isdigit() and path.startswith("edgar/data/")):
            continue
        out.append(
            IndexEntry(
                form=form,
                company=" ".join(parts[1:-3]),
                cik=int(cik),
                filed=date(int(filed[:4]), int(filed[4:6]), int(filed[6:8])),
                path=path,
            )
        )
    return out


# ── Form 4 ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Owner:
    name: str
    is_director: bool
    is_officer: bool
    title: str


@dataclass(frozen=True)
class Transaction:
    day: str  # YYYY-MM-DD
    code: str  # P = open-market purchase, S = sale, A = grant, G = gift…
    acquired: bool  # A (acquired) vs D (disposed)
    shares: float
    price: float  # per share, 0 when the filing leaves it blank


@dataclass(frozen=True)
class Form4:
    accession: str
    issuer: str
    symbol: str
    cik: int  # issuer
    owners: tuple[Owner, ...]
    transactions: tuple[Transaction, ...]


def form4(entry: IndexEntry) -> Form4 | None:
    """One Form 4, or None when the document carries no readable ownership block."""
    body = _get(f"{config().edgar.archives_url}/{entry.path}", ttl_hours=0, cache=False)
    return parse_form4(body, accession=entry.accession)


_OWNERSHIP = re.compile(r"<ownershipDocument>.*?</ownershipDocument>", re.S)
_OWNER = re.compile(r"<reportingOwner>(.*?)</reportingOwner>", re.S)
_NON_DERIVATIVE = re.compile(r"<nonDerivativeTransaction>(.*?)</nonDerivativeTransaction>", re.S)


def parse_form4(body: str, *, accession: str) -> Form4 | None:
    found = _OWNERSHIP.search(body)
    if found is None:
        return None
    doc = found.group(0)
    owners = tuple(
        Owner(
            name=_text(block, "rptOwnerName"),
            is_director=_flag(block, "isDirector"),
            is_officer=_flag(block, "isOfficer"),
            title=_text(block, "officerTitle"),
        )
        for block in _OWNER.findall(doc)
    )
    transactions: list[Transaction] = []
    for block in _NON_DERIVATIVE.findall(doc):
        try:
            transactions.append(
                Transaction(
                    day=_text(block, "transactionDate"),
                    code=_text(block, "transactionCode"),
                    acquired=_text(block, "transactionAcquiredDisposedCode") == "A",
                    shares=float(_text(block, "transactionShares") or 0),
                    price=float(_text(block, "transactionPricePerShare") or 0),
                )
            )
        except ValueError:
            continue
    return Form4(
        accession=accession,
        issuer=_text(doc, "issuerName"),
        symbol=_text(doc, "issuerTradingSymbol").upper(),
        cik=int(_text(doc, "issuerCik") or 0),
        owners=owners,
        transactions=tuple(transactions),
    )


def _text(block: str, tag: str) -> str:
    """The text of the first <tag>, looking through a nested <value> when there is one."""
    found = re.search(rf"<(?:\w+:)?{tag}>(.*?)</(?:\w+:)?{tag}>", block, re.S)
    if found is None:
        return ""
    inner = found.group(1)
    value = re.search(r"<(?:\w+:)?value>(.*?)</(?:\w+:)?value>", inner, re.S)
    return (value.group(1) if value else inner).strip()


def _flag(block: str, tag: str) -> bool:
    return _text(block, tag).lower() in {"1", "true"}


# ── 13F-HR ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Filing13F:
    cik: int
    accession: str  # with dashes, as EDGAR prints it
    filed: date
    period: str  # YYYY-MM-DD, the quarter end

    @property
    def folder(self) -> str:
        return (
            f"{config().edgar.archives_url}/edgar/data/{self.cik}/{self.accession.replace('-', '')}"
        )


@dataclass(frozen=True)
class Holding:
    cusip: str
    name: str
    value_usd: float
    shares: float


def filings_13f(cik: int, *, limit: int = 4) -> list[Filing13F]:
    """The manager's latest 13F-HR filings, newest first (amendments left out)."""
    cfg = config().edgar
    body = _get(f"{cfg.submissions_url}/CIK{cik:010d}.json", ttl_hours=24)
    try:
        recent = json.loads(body)["filings"]["recent"]
        rows = zip(
            recent["form"],
            recent["accessionNumber"],
            recent["filingDate"],
            recent["reportDate"],
            strict=True,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise DataSourceError(f"Fiche EDGAR illisible pour le CIK {cik}: {exc}") from exc
    out = [
        Filing13F(cik=cik, accession=acc, filed=date.fromisoformat(filed), period=period)
        for form, acc, filed, period in rows
        if form == "13F-HR"
    ]
    return out[:limit]


_INFO_TABLE = re.compile(r"<(?:\w+:)?infoTable(?:\s[^>]*)?>(.*?)</(?:\w+:)?infoTable>", re.S)


def holdings_13f(filing: Filing13F) -> dict[str, Holding]:
    """The filing's positions by CUSIP, the same security's lines added together."""
    folder = filing.folder
    listing = _get(f"{folder}/index.json", ttl_hours=168)
    try:
        names = [item["name"] for item in json.loads(listing)["directory"]["item"]]
    except (ValueError, KeyError, TypeError) as exc:
        raise DataSourceError(f"Dossier 13F illisible ({filing.accession}): {exc}") from exc
    tables = [n for n in names if n.lower().endswith(".xml") and n != "primary_doc.xml"]
    if not tables:
        raise DataSourceError(f"Aucun tableau de positions dans le 13F {filing.accession}.")
    return parse_13f(_get(f"{folder}/{tables[0]}", ttl_hours=168))


# A manager files a 13F only above 100 M$. Values are in dollars since 2023,
# yet some filers still write thousands, as the form did for thirty years: a
# table that adds up to less than the filing threshold is one of those.
_FILING_THRESHOLD_USD = 100_000_000


def parse_13f(body: str) -> dict[str, Holding]:
    out = _parse_13f(body)
    if out and sum(h.value_usd for h in out.values()) < _FILING_THRESHOLD_USD:
        out = {
            cusip: Holding(h.cusip, h.name, h.value_usd * 1000, h.shares)
            for cusip, h in out.items()
        }
    return out


def _parse_13f(body: str) -> dict[str, Holding]:
    out: dict[str, Holding] = {}
    for block in _INFO_TABLE.findall(body):
        cusip = _text(block, "cusip").upper()
        if not cusip:
            continue
        try:
            value = float(_text(block, "value") or 0)
            shares = float(_text(block, "sshPrnamt") or 0)
        except ValueError:
            continue
        prior = out.get(cusip)
        out[cusip] = Holding(
            cusip=cusip,
            name=_text(block, "nameOfIssuer") or (prior.name if prior else ""),
            value_usd=value + (prior.value_usd if prior else 0.0),
            shares=shares + (prior.shares if prior else 0.0),
        )
    return out
