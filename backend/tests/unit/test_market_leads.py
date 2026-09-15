"""« Pistes de marché » (ADR-033): parsers on captured payloads, rules on plain rows."""

from __future__ import annotations

import json
from datetime import date

import pytest

from app.data import edgar, polymarket
from app.finance import market_leads
from app.llm import prompt_builder
from app.models import MarketLead

INDEX = """Description:           Daily Index of EDGAR Dissemination Feed by Form Type
Last Data Received:    Sep 14, 2026

Form Type   Company Name                                                  CIK         Date Filed  File Name
---------------------------------------------------------------------------------------------------------------
1-A              Andrew Arroyo Real Estate Inc.                                1861089     20260914    edgar/data/1861089/0001477932-26-005545.txt
4                8X8 INC /DE/                                                  1023731     20260914    edgar/data/1023731/0001023731-26-000151.txt
4/A              Some Corp                                                     1000001     20260914    edgar/data/1000001/0001000001-26-000001.txt
4                2025 Irrevocable Two-Year Grantor Retained Annuity Trust of   2102046     20260914    edgar/data/2102046/0002082289-26-000013.txt
"""

FORM4 = """<SEC-DOCUMENT>0001023731-26-000151.txt : 20260914
<XML>
<?xml version="1.0"?>
<ownershipDocument>
    <issuer>
        <issuerCik>0001023731</issuerCik>
        <issuerName>8X8 INC /DE/</issuerName>
        <issuerTradingSymbol>eght</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId><rptOwnerName>Doe Jane</rptOwnerName></reportingOwnerId>
        <reportingOwnerRelationship>
            <isDirector>0</isDirector>
            <isOfficer>1</isOfficer>
            <officerTitle>Chief Executive Officer</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <transactionDate><value>2026-09-11</value></transactionDate>
            <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
            <transactionAmounts>
                <transactionShares><value>50000</value></transactionShares>
                <transactionPricePerShare><value>2.50</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
        </nonDerivativeTransaction>
        <nonDerivativeTransaction>
            <transactionDate><value>2026-09-11</value></transactionDate>
            <transactionCoding><transactionCode>A</transactionCode></transactionCoding>
            <transactionAmounts>
                <transactionShares><value>1000</value></transactionShares>
                <transactionPricePerShare><value></value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
</XML>
"""

TABLE_13F = """<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
  <infoTable>
    <nameOfIssuer>ALLY FINL INC</nameOfIssuer>
    <cusip>02005N100</cusip>
    <value>577211815</value>
    <shrsOrPrnAmt><sshPrnamt>12561737</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
  </infoTable>
  <infoTable>
    <nameOfIssuer>ALLY FINL INC</nameOfIssuer>
    <cusip>02005N100</cusip>
    <value>128838056</value>
    <shrsOrPrnAmt><sshPrnamt>2803875</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
  </infoTable>
  <ns1:infoTable xmlns:ns1="http://www.sec.gov/edgar/document/thirteenf/informationtable">
    <ns1:nameOfIssuer>APPLE INC</ns1:nameOfIssuer>
    <ns1:cusip>037833100</ns1:cusip>
    <ns1:value>60000000000</ns1:value>
    <ns1:shrsOrPrnAmt><ns1:sshPrnamt>300000000</ns1:sshPrnamt></ns1:shrsOrPrnAmt>
  </ns1:infoTable>
</informationTable>
"""

GAMMA_EVENT = {
    "id": "481717",
    "title": "Fed Decision in September?",
    "slug": "fed-decision-in-september-762",
    "tags": [{"slug": "fed"}, {"slug": "economy"}],
    "markets": [
        {
            "question": "No change",
            "outcomePrices": '["0.115", "0.885"]',
            "oneDayPriceChange": -0.05,
            "oneWeekPriceChange": -0.35,
            "volume24hr": 6227170.25,
            "endDate": "2026-09-16T00:00:00Z",
        },
        {
            "question": "Cut by 25 bps",
            "outcomePrices": '["0.87", "0.13"]',
            "oneWeekPriceChange": 0.34,
            "volume24hr": 5187524.0,
        },
        {"question": "Closed one", "closed": True, "outcomePrices": '["1", "0"]'},
    ],
}


# ── EDGAR parsers ───────────────────────────────────────────────────────────


def test_index_keeps_the_exact_form_type_and_reads_names_with_spaces():
    entries = edgar.parse_index(INDEX, "4")
    assert [e.cik for e in entries] == [1023731, 2102046]
    assert entries[0].company == "8X8 INC /DE/"
    assert entries[0].filed == date(2026, 9, 14)
    assert entries[0].accession == "0001023731-26-000151"
    assert entries[1].company.startswith("2025 Irrevocable")


def test_form4_reads_issuer_owner_and_transactions_through_value_tags():
    filing = edgar.parse_form4(FORM4, accession="0001023731-26-000151")
    assert filing is not None
    assert filing.symbol == "EGHT"
    assert filing.cik == 1023731
    assert filing.owners[0].is_officer and not filing.owners[0].is_director
    assert filing.owners[0].title == "Chief Executive Officer"
    codes = [(t.code, t.shares, t.price, t.acquired) for t in filing.transactions]
    assert codes == [("P", 50000.0, 2.5, True), ("A", 1000.0, 0.0, True)]


def test_form4_without_ownership_block_is_none():
    assert edgar.parse_form4("<SEC-DOCUMENT>nothing here</SEC-DOCUMENT>", accession="x") is None


def test_13f_adds_the_same_cusip_together_and_reads_namespaced_tables():
    holdings = edgar.parse_13f(TABLE_13F)
    assert holdings["02005N100"].shares == pytest.approx(12561737 + 2803875)
    assert holdings["02005N100"].value_usd == pytest.approx(577211815 + 128838056)
    assert holdings["037833100"].name == "APPLE INC"


def test_13f_written_in_thousands_is_read_in_dollars():
    table = (
        TABLE_13F.replace("60000000000", "60000000")
        .replace("577211815", "577211")
        .replace("128838056", "128838")
    )
    holdings = edgar.parse_13f(table)
    assert holdings["037833100"].value_usd == pytest.approx(60_000_000_000)
    assert holdings["02005N100"].value_usd == pytest.approx((577211 + 128838) * 1000)


# ── Polymarket parser ───────────────────────────────────────────────────────


def test_markets_decode_the_string_encoded_prices_and_skip_closed_ones():
    markets = polymarket.markets(GAMMA_EVENT)
    assert [m.question for m in markets] == ["No change", "Cut by 25 bps"]
    assert markets[0].yes_price == pytest.approx(0.115)
    assert markets[0].week_change == pytest.approx(-0.35)
    assert markets[0].url.endswith("/event/fed-decision-in-september-762")
    assert markets[0].tags == ("fed", "economy")


# ── Rules ───────────────────────────────────────────────────────────────────


def test_polymarket_leads_flag_the_weekly_move_and_the_leading_outcome():
    rules = market_leads.PolymarketRules(tags=["fed"], min_volume_24h_usd=1000, min_week_move=0.3)
    leads = market_leads._polymarket_leads(
        [polymarket.markets(GAMMA_EVENT)], rules, date(2026, 9, 15)
    )
    kinds = [(lead.kind, lead.detail) for lead in leads]
    assert len([k for k, _ in kinds if k == "prediction_move"]) == 2
    state = [d for k, d in kinds if k == "prediction_state"]
    assert state == ["Issue la plus probable : « Cut by 25 bps » à 87%, +34 points sur la semaine"]


def _purchase(symbol: str, owner: str, amount: float, filed: str) -> dict:
    return {
        "accession": f"{symbol}-{owner}",
        "cik": 1,
        "issuer": f"{symbol} Corp",
        "symbol": symbol,
        "owner": owner,
        "title": "CEO",
        "amount_usd": amount,
        "day": filed,
        "filed": filed,
    }


def test_insider_rules_group_distinct_buyers_and_flag_a_lone_big_buy():
    rules = market_leads.InsiderRules(
        min_purchase_usd=100_000, big_purchase_usd=1_000_000, cluster_days=30, min_insiders=2
    )
    rows = [
        _purchase("ABC", "Doe Jane", 150_000, "2026-09-10"),
        _purchase("ABC", "Roe Rick", 200_000, "2026-09-12"),
        _purchase("ABC", "Doe Jane", 120_000, "2026-09-14"),  # same buyer twice: one insider
        _purchase("XYZ", "Poe Paul", 2_500_000, "2026-09-13"),
        _purchase("OLD", "Moe Mia", 5_000_000, "2026-07-01"),  # outside the window
        _purchase("SML", "Zoe Zed", 300_000, "2026-09-13"),  # alone and small: nothing
    ]
    leads = market_leads._insider_leads(rows, rules, date(2026, 9, 15))
    by_symbol = {lead.symbols[0]: lead for lead in leads}
    assert set(by_symbol) == {"ABC", "XYZ"}
    assert by_symbol["ABC"].kind == "insider_cluster"
    assert "470,000 $" in by_symbol["ABC"].detail
    assert by_symbol["XYZ"].kind == "insider_buy"


def test_purchases_of_keeps_open_market_buys_by_insiders_only():
    rules = market_leads.InsiderRules(min_purchase_usd=100_000)
    filing = edgar.parse_form4(FORM4, accession="a")
    assert filing is not None
    rows = market_leads._purchases_of(filing, rules)
    assert rows == [
        {
            "accession": "a",
            "cik": 1023731,
            "issuer": "8X8 INC /DE/",
            "symbol": "EGHT",
            "owner": "Doe Jane",
            "title": "Chief Executive Officer",
            "amount_usd": 125000.0,
            "day": "2026-09-11",
        }
    ]
    small = market_leads.InsiderRules(min_purchase_usd=200_000)
    assert market_leads._purchases_of(filing, small) == []


def test_fund_diff_reports_new_lines_exits_and_big_changes_largest_first():
    rules = market_leads.FundRules(
        followed=[], min_position_usd=1_000, min_change_pct=0.25, max_leads_per_filing=10
    )
    manager = market_leads.Manager(name="Berkshire Hathaway", cik=1067983)
    filing = edgar.Filing13F(
        cik=1067983, accession="0001-26-1", filed=date(2026, 8, 14), period="2026-06-30"
    )
    now = {
        "A": edgar.Holding("A", "APPLE INC", 60_000, 300),
        "B": edgar.Holding("B", "NEW CO", 5_000, 100),
        "C": edgar.Holding("C", "STEADY INC", 9_000, 100),
        "T": edgar.Holding("T", "TINY", 10, 1),
    }
    before = {
        "A": edgar.Holding("A", "APPLE INC", 90_000, 450),
        "C": edgar.Holding("C", "STEADY INC", 9_500, 105),
        "E": edgar.Holding("E", "GONE CORP", 7_000, 70),
        "T": edgar.Holding("T", "TINY", 10, 1),
    }
    leads = market_leads._fund_diff(manager, filing, now, before, rules)
    assert [(lead.kind, lead.title) for lead in leads] == [
        ("fund_change", "Berkshire Hathaway : allège Apple Inc"),
        ("fund_exit", "Berkshire Hathaway : sort de Gone Corp"),
        ("fund_new_position", "Berkshire Hathaway : nouvelle ligne New Co"),
    ]
    assert "-33%" in leads[0].detail
    assert leads[0].observed_at == "2026-08-14"


def test_fund_leads_reuse_the_stored_diff_until_a_new_filing_and_expire_it(monkeypatch):
    rules = market_leads.FundRules(
        followed=[market_leads.Manager(name="Fund", cik=42)], keep_days=21
    )
    filing = edgar.Filing13F(
        cik=42, accession="acc-1", filed=date(2026, 8, 14), period="2026-06-30"
    )
    monkeypatch.setattr(edgar, "filings_13f", lambda cik, limit=4: [filing])
    monkeypatch.setattr(
        edgar, "holdings_13f", lambda f: pytest.fail("holdings must not be fetched again")
    )
    stored = {
        "42": {
            "accession": "acc-1",
            "filed": "2026-08-14",
            "leads": [
                MarketLead(
                    source="edgar_13f",
                    kind="fund_exit",
                    title="Fund : sort de X",
                    detail="d",
                    url="u",
                    observed_at="2026-08-14",
                ).model_dump()
            ],
        }
    }
    leads, state = market_leads.fund_leads(rules, stored, date(2026, 8, 20))
    assert [lead.title for lead in leads] == ["Fund : sort de X"]
    assert state == stored
    later, _ = market_leads.fund_leads(rules, stored, date(2026, 9, 20))
    assert later == []


# ── Store and prompt ────────────────────────────────────────────────────────


def test_refresh_survives_a_source_down_and_serves_from_memory(monkeypatch, tmp_path):
    monkeypatch.setattr(market_leads, "_PATH", tmp_path / "leads.json")
    monkeypatch.setattr(market_leads, "_STATE", tmp_path / "state.json")
    monkeypatch.setattr(market_leads, "_MEMORY", None)
    lead = MarketLead(
        source="polymarket",
        kind="prediction_state",
        title="t",
        detail="d",
        url="u",
        observed_at="2026-09-15",
        weight=0.3,
    )
    monkeypatch.setattr(market_leads, "polymarket_leads", lambda rules, today: [lead])
    monkeypatch.setattr(
        market_leads,
        "insider_leads",
        lambda rules, state, today: (_ for _ in ()).throw(OSError("x")),
    )
    monkeypatch.setattr(market_leads, "fund_leads", lambda rules, state, today: ([], {"kept": 1}))

    out = market_leads.refresh(date(2026, 9, 15))

    assert [lead.title for lead in out.leads] == ["t"]
    assert json.loads((tmp_path / "state.json").read_text()) == {"funds": {"kept": 1}}
    assert market_leads.load() is not None
    assert market_leads.load().leads[0].title == "t"


def test_prompt_lists_the_raw_leads_and_the_system_prompt_asks_for_the_triage():
    lead = MarketLead(
        source="edgar_form4",
        kind="insider_cluster",
        title="ACME (ACM) : 3 dirigeants achètent",
        detail="1,200,000 $ d'achats",
        url="https://sec.gov/x",
        observed_at="2026-09-15",
    )
    snapshot = {
        "snapshot_at": "2026-09-15T06:00:00",
        "profile": {
            k: None
            for k in (
                "age",
                "fiscal_shares",
                "rfr_n_minus_2_eur",
                "horizon_years",
                "target_annual_return_pct",
                "max_annual_volatility_pct",
                "default_broker",
            )
        },
        "net_worth_eur": 1.0,
        "total_assets_eur": 1.0,
        "total_liabilities_eur": 0.0,
        "checking_total_eur": 1.0,
        "pea_cash_total_eur": 0.0,
        "envelopes": [],
        "investment_accounts": [],
        "loans": [],
        "market_leads": [
            {
                "source": lead.source,
                "title": lead.title,
                "detail": lead.detail,
                "url": lead.url,
                "observed_at": lead.observed_at,
            }
        ],
    }
    prompt = prompt_builder.build_user_prompt(snapshot)
    assert "## Pistes de marché" in prompt
    assert "[edgar_form4] ACME (ACM) : 3 dirigeants achètent — 1,200,000 $ d'achats" in prompt
    assert "# Pistes à regarder" in prompt_builder.SYSTEM_PROMPT
    assert "jamais un ordre" in prompt_builder.SYSTEM_PROMPT
