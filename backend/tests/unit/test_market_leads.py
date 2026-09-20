"""« Pistes de marché » (ADR-033): parsers on captured payloads, rules on plain rows."""

from __future__ import annotations

import json
from datetime import date

import pytest

from app.data import cftc, edgar, kalshi, polymarket
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

INDEX_13D = """Form Type   Company Name                                                  CIK         Date Filed  File Name
---------------------------------------------------------------------------------------------------------------
SCHEDULE 13D     Strategic Value Partners, LLC                                 1301912     20260918    edgar/data/1301912/0001193805-26-001000.txt
SCHEDULE 13D/A   Some Amender                                                  1000002     20260918    edgar/data/1000002/0001000002-26-000002.txt
SCHEDULE 13G     Some Passive                                                  1000003     20260918    edgar/data/1000003/0001000003-26-000003.txt
"""

SCHEDULE_13D = """<SEC-DOCUMENT>0001193805-26-001000.txt : 20260918
<XML>
<edgarSubmission xmlns="http://www.sec.gov/edgar/schedule13D" xmlns:com="http://www.sec.gov/edgar/common">
  <formData>
    <coverPageHeader>
      <securitiesClassTitle>Common Stock</securitiesClassTitle>
      <dateOfEvent>09/16/2026</dateOfEvent>
      <issuerInfo>
        <issuerCIK>0000807882</issuerCIK>
        <issuerCusips><issuerCusipNumber>466367109</issuerCusipNumber></issuerCusips>
        <issuerName>JACK IN THE BOX INC</issuerName>
      </issuerInfo>
    </coverPageHeader>
    <reportingPersons>
      <reportingPersonInfo>
        <reportingPersonCIK>0001517137</reportingPersonCIK>
        <reportingPersonName>Starboard Value LP</reportingPersonName>
        <aggregateAmountOwned>1500000.00</aggregateAmountOwned>
        <percentOfClass>7.90</percentOfClass>
      </reportingPersonInfo>
      <reportingPersonInfo>
        <reportingPersonCIK>0001517138</reportingPersonCIK>
        <reportingPersonName>Starboard Value GP LLC</reportingPersonName>
        <aggregateAmountOwned>1500000.00</aggregateAmountOwned>
        <percentOfClass>7.90</percentOfClass>
      </reportingPersonInfo>
    </reportingPersons>
  </formData>
</edgarSubmission>
</XML>
"""

COT_ROWS = json.dumps(
    [
        {
            "report_date_as_yyyy_mm_dd": "2026-09-15T00:00:00.000",
            "lev_money_positions_long": "300000",
            "lev_money_positions_short": "100000",
            "open_interest_all": "2000000",
        },
        {  # the same week listed again for another exchange: ignored
            "report_date_as_yyyy_mm_dd": "2026-09-15T00:00:00.000",
            "lev_money_positions_long": "1",
            "lev_money_positions_short": "1",
            "open_interest_all": "1",
        },
        {
            "report_date_as_yyyy_mm_dd": "2026-09-08T00:00:00.000",
            "lev_money_positions_long": "150000",
            "lev_money_positions_short": "200000",
            "open_interest_all": "2000000",
        },
    ]
)

KALSHI_PAGE = json.dumps(
    {
        "markets": [
            {
                "ticker": "KXFEDDECISION-26OCT-H25",
                "event_ticker": "KXFEDDECISION-26OCT",
                "title": "Will the Fed hike by 25 bps in October 2026?",
                "last_price_dollars": "0.5600",
                "volume_24h_fp": "40000.00",
                "open_interest_fp": "900000.00",
                "close_time": "2026-10-28T18:00:00Z",
            },
            {
                "ticker": "KXFEDDECISION-26OCT-N",
                "event_ticker": "KXFEDDECISION-26OCT",
                "title": "Will the Fed hold in October 2026?",
                "last_price_dollars": "0",
                "yes_bid_dollars": "0.40",
                "yes_ask_dollars": "0.44",
                "volume_24h_fp": "52000.00",
                "open_interest_fp": "500000.00",
                "close_time": "2026-10-28T18:00:00Z",
            },
            {
                "ticker": "KXFEDDECISION-27APR-H25",
                "event_ticker": "KXFEDDECISION-27APR",
                "title": "Will the Fed hike in April 2027?",
                "last_price_dollars": "0.1000",
                "volume_24h_fp": "12.00",
                "close_time": "2027-04-28T18:00:00Z",
            },
        ],
        "cursor": "",
    }
)

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


def test_index_matches_a_form_type_written_in_two_words():
    entries = edgar.parse_index(INDEX_13D, "SCHEDULE 13D")
    assert [(e.company, e.cik, e.accession) for e in entries] == [
        ("Strategic Value Partners, LLC", 1301912, "0001193805-26-001000")
    ]
    assert edgar.parse_index(INDEX_13D, "SCHEDULE 13G")[0].company == "Some Passive"


def test_13d_reads_issuer_event_day_and_every_reporting_person():
    filing = edgar.parse_13d(SCHEDULE_13D, accession="0001193805-26-001000")
    assert filing is not None
    assert (filing.issuer, filing.issuer_cik, filing.cusip) == (
        "JACK IN THE BOX INC",
        807882,
        "466367109",
    )
    assert filing.event_day == "2026-09-16"
    assert [(p.name, p.cik, p.percent, p.shares) for p in filing.persons] == [
        ("Starboard Value LP", 1517137, 7.9, 1_500_000.0),
        ("Starboard Value GP LLC", 1517138, 7.9, 1_500_000.0),
    ]
    assert filing.folder.endswith("/edgar/data/807882/000119380526001000")
    assert edgar.parse_13d("<html>an old free-form 13D</html>", accession="x") is None


def test_activist_leads_keep_followed_filers_only_and_remember_the_filing(monkeypatch):
    entries = edgar.parse_index(INDEX_13D, "SCHEDULE 13D")
    monkeypatch.setattr(market_leads.edgar, "daily_index", lambda day, form: entries)
    monkeypatch.setattr(
        market_leads.edgar,
        "schedule_13d",
        lambda entry: edgar.parse_13d(SCHEDULE_13D, accession=entry.accession),
    )
    rules = market_leads.ActivistRules(
        followed=[market_leads.Manager(name="Starboard Value", cik=1517137)],
        index_lookback_days=2,
    )
    leads, state = market_leads.activist_leads(rules, {}, date(2026, 9, 20))
    assert [lead.title for lead in leads] == ["Starboard Value : 7.9 % de Jack In The Box Inc"]
    assert leads[0].kind == "activist_stake" and leads[0].observed_at == "2026-09-18"
    assert "seuil franchi le 2026-09-16" in leads[0].detail
    assert set(state["seen"]) == {"0001193805-26-001000"}

    # A second night: the filing is remembered, the lead is kept, nothing is fetched.
    monkeypatch.setattr(
        market_leads.edgar, "schedule_13d", lambda entry: (_ for _ in ()).throw(AssertionError)
    )
    again, _ = market_leads.activist_leads(rules, state, date(2026, 9, 21))
    assert [lead.title for lead in again] == [lead.title for lead in leads]

    monkeypatch.setattr(
        market_leads.edgar,
        "schedule_13d",
        lambda entry: edgar.parse_13d(SCHEDULE_13D, accession=entry.accession),
    )
    nobody = market_leads.ActivistRules(followed=[market_leads.Manager(name="X", cik=1)])
    assert market_leads.activist_leads(nobody, {}, date(2026, 9, 20))[0] == []


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


def test_polymarket_leads_flag_the_largest_weekly_move_and_the_leading_outcome():
    rules = market_leads.PolymarketRules(
        tags=["fed"], min_volume_24h_usd=1000, min_week_move=0.3, min_days_to_resolution=0
    )
    leads = market_leads._polymarket_leads(
        [polymarket.markets(GAMMA_EVENT)], rules, date(2026, 9, 15)
    )
    kinds = [(lead.kind, lead.detail) for lead in leads]
    # Two rungs of the same event moved: one lead, the largest move.
    moves = [d for k, d in kinds if k == "prediction_move"]
    assert len(moves) == 1 and moves[0].startswith("« No change » : 12% de oui, -35 points")
    state = [d for k, d in kinds if k == "prediction_state"]
    assert state == ["Issue la plus probable : « Cut by 25 bps » à 87%, +34 points sur la semaine"]


def _market(event: str, question: str, *, volume: float, end: str = "", move: float = 0.0):
    return polymarket.Market(
        event_id=event,
        event_title=event,
        event_slug=event,
        question=question,
        yes_price=0.5,
        day_change=0.0,
        week_change=move,
        volume_24h_usd=volume,
        end_date=end,
        tags=(),
    )


def test_polymarket_ignores_bets_settled_within_days_and_fills_the_state_from_traded_ones():
    rules = market_leads.PolymarketRules(
        tags=[],
        min_volume_24h_usd=1000,
        min_week_move=0.3,
        min_days_to_resolution=14,
        max_state_leads=2,
    )
    today = date(2026, 9, 20)
    events = [
        [_market("Bitcoin above X on Sept 21?", "yes", volume=900_000, end="2026-09-21", move=0.5)],
        [_market("Fed in October?", "hold", volume=50_000, end="2026-10-28T00:00:00Z", move=0.4)],
        [_market("Thin market", "yes", volume=10, end="2027-01-01", move=0.9)],
        [_market("Recession in 2027?", "yes", volume=20_000, move=0.1)],
    ]
    leads = market_leads._polymarket_leads(events, rules, today)
    moves = [lead.title for lead in leads if lead.kind == "prediction_move"]
    state = [lead.title for lead in leads if lead.kind == "prediction_state"]
    assert moves == ["Fed in October?"]
    # The daily bet and the thin market never enter the ranking, so the two
    # state slots go to bets that are actually traded.
    assert state == ["Fed in October?", "Recession in 2027?"]


def test_insider_leads_look_back_over_the_days_the_sec_has_published(monkeypatch):
    asked: list[date] = []
    monkeypatch.setattr(
        market_leads.edgar, "daily_index", lambda day, form: asked.append(day) or []
    )
    rules = market_leads.InsiderRules(index_lookback_days=3)
    leads, state = market_leads.insider_leads(rules, {}, date(2026, 9, 20))
    assert asked == [date(2026, 9, 17), date(2026, 9, 18), date(2026, 9, 19)]
    assert leads == [] and state == {"seen": {}, "purchases": []}


def test_daily_index_is_empty_when_the_sec_has_no_file_yet(monkeypatch):
    def refuse(url, *, ttl_hours, cache=True):
        raise market_leads.DataSourceError(f"{url} a répondu 403.")

    monkeypatch.setattr(edgar.http, "get_text", refuse)
    assert edgar.daily_index(date(2026, 9, 19), "4") == []


def test_cot_rows_become_weeks_newest_first_and_a_duplicate_week_is_dropped():
    weeks = cftc.parse_positions(COT_ROWS, "financial")
    assert [(w.day, w.spec_long, w.spec_short) for w in weeks] == [
        ("2026-09-15", 300_000.0, 100_000.0),
        ("2026-09-08", 150_000.0, 200_000.0),
    ]
    assert weeks[0].net_share == 0.1 and weeks[1].net_share == -0.025


def _week(day: str, net: float) -> cftc.Week:
    return cftc.Week(
        day=day, spec_long=1_000 * (1 + net), spec_short=1_000 * (1 - net), open_interest=2_000
    )


def test_positioning_flags_a_one_year_extreme_or_a_change_of_side_only():
    rules = market_leads.PositioningRules(contracts=[], weeks=52, min_net_share=0.05)
    gold = market_leads.Contract(name="GOLD", dataset="commodities", label="Or")
    calm = [_week("2026-09-15", 0.10)] + [
        _week(f"2026-0{i}-01", net) for i, net in ((1, 0.12), (2, 0.05), (3, 0.15), (4, 0.08))
    ]
    assert market_leads._positioning_lead(gold, calm, rules) is None

    high = [_week("2026-09-15", 0.3), *calm[1:]]
    lead = market_leads._positioning_lead(gold, high, rules)
    assert lead is not None and lead.kind == "positioning_extreme"
    assert lead.title == "Or : les spéculateurs jamais aussi acheteurs depuis un an"
    assert "+30% de l'intérêt ouvert au 2026-09-15, contre +12%" in lead.detail
    assert "gestion spéculative" in lead.detail

    flip = [_week("2026-09-15", -0.08), _week("2026-09-08", 0.05), _week("2026-09-01", -0.20)]
    lead = market_leads._positioning_lead(gold, flip + calm[1:], rules)
    assert lead is not None and lead.kind == "positioning_flip"
    assert lead.title == "Or : les spéculateurs passent vendeurs"

    tiny = [_week("2026-09-15", 0.01)] + [_week("2026-08-01", 0.0)] * 4
    assert market_leads._positioning_lead(gold, tiny, rules) is None
    assert market_leads._positioning_lead(gold, high[:3], rules) is None  # too short


def test_kalshi_markets_read_the_price_the_book_and_the_cursor():
    page, cursor = kalshi.parse_markets(KALSHI_PAGE, "KXFEDDECISION")
    assert cursor == ""
    assert [(m.ticker, m.yes_price, m.volume_24h) for m in page] == [
        ("KXFEDDECISION-26OCT-H25", 0.56, 40_000.0),
        ("KXFEDDECISION-26OCT-N", 0.42, 52_000.0),
        ("KXFEDDECISION-27APR-H25", 0.1, 12.0),
    ]
    assert page[0].url == "https://kalshi.com/markets/kxfeddecision"


def test_kalshi_leads_remember_prices_and_read_the_move_a_week_later(monkeypatch):
    page, _ = kalshi.parse_markets(KALSHI_PAGE, "KXFEDDECISION")
    monkeypatch.setattr(market_leads.kalshi, "markets", lambda series: page)
    rules = market_leads.KalshiRules(
        series=["KXFEDDECISION"], min_volume_24h=1_000, min_week_move=0.15, max_state_leads=6
    )
    # First night: no memory, so only the state of expectations — the most
    # traded market of the event, not the highest price. April is too thin.
    leads, state = market_leads.kalshi_leads(rules, {}, date(2026, 9, 13))
    assert [(lead.kind, lead.title) for lead in leads] == [
        ("prediction_state", "Will the Fed hold in October 2026?")
    ]
    assert "à 42% de oui" in leads[0].detail and "92,000 $" in leads[0].detail
    assert state["prices"]["KXFEDDECISION-26OCT-H25"] == {"2026-09-13": 0.56}

    # A week later the hike went from 20 % to 56 %: a move, and the thin April market never counts.
    state["prices"]["KXFEDDECISION-26OCT-H25"] = {"2026-09-13": 0.20}
    leads, state = market_leads.kalshi_leads(rules, state, date(2026, 9, 20))
    kinds = {lead.kind: lead for lead in leads}
    assert kinds["prediction_move"].title == "Will the Fed hike by 25 bps in October 2026?"
    assert kinds["prediction_move"].detail.startswith("56% de oui, +36 points en une semaine")
    assert kinds["prediction_state"].title == "Will the Fed hold in October 2026?"
    assert set(state["prices"]["KXFEDDECISION-26OCT-H25"]) == {"2026-09-13", "2026-09-20"}

    # Memory is pruned: a price older than the window is forgotten.
    state["prices"]["KXFEDDECISION-26OCT-H25"]["2026-08-01"] = 0.1
    _, state = market_leads.kalshi_leads(rules, state, date(2026, 9, 21))
    assert "2026-08-01" not in state["prices"]["KXFEDDECISION-26OCT-H25"]


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
    monkeypatch.setattr(market_leads, "activist_leads", lambda rules, state, today: ([], {}))
    monkeypatch.setattr(market_leads, "positioning_leads", lambda rules, today: [])
    monkeypatch.setattr(market_leads, "kalshi_leads", lambda rules, state, today: ([], {}))

    out = market_leads.refresh(date(2026, 9, 15))

    assert [lead.title for lead in out.leads] == ["t"]
    assert json.loads((tmp_path / "state.json").read_text()) == {
        "funds": {"kept": 1},
        "activists": {},
        "kalshi": {},
    }
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
