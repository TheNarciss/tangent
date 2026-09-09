"""Parsers of the external sources, on captured payloads.

No test here touches the network: the shape of each provider's answer is
pinned as a literal. Whether the sources still *answer* is checked by
`python -m app.data.probe`, which is a manual command on purpose.
"""

import io
import zipfile

import pytest

from app.data import ecb, eurostat, fred, http, ken_french, lbma, openfigi
from app.data.config import config
from app.errors import DataSourceError

FRED_CSV = """observation_date,IRLTLT01FRM156N
1960-01-01,5.82
1960-02-01,.
1960-03-01,5.90
"""

ECB_CSV = """KEY,FREQ,REF_AREA,CURRENCY,TIME_PERIOD,OBS_VALUE,OBS_STATUS
EXR.D.USD.EUR.SP00.A,D,U2,EUR,2026-09-08,1.1614,A
EXR.D.USD.EUR.SP00.A,D,U2,EUR,2026-09-04,1.1620,A
"""

EUROSTAT_JSON = """{
  "value": {"0": 100.0, "12": 102.5},
  "dimension": {"time": {"category": {"index": {"2025-01": 0, "2026-01": 12}}}}
}"""

KEN_FRENCH_CSV = """This file was created using the 202607 Bloomberg database.

Missing data are indicated by -99.99.

,Mkt-RF,SMB,HML,RF
199007    ,0.77    ,0.53   ,-0.36    ,0.68
199008   ,-9.99    ,0.10    ,0.10    ,0.60
199009  ,-99.99    ,0.10    ,0.10    ,0.60

  Annual Factors: January-December

,Mkt-RF,SMB,HML,RF
2008  ,-42.00   ,-2.17    ,2.34    ,1.60
"""


@pytest.fixture(autouse=True)
def _clear_cache():
    http.clear_cache()
    yield
    http.clear_cache()


def _zip_of(csv: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr("Developed_3_Factors.csv", csv)
    return buffer.getvalue()


def test_fred_drops_missing_observations(monkeypatch):
    monkeypatch.setattr(http, "get_text", lambda *a, **k: FRED_CSV)

    series = fred.named("oat_10y")

    assert len(series) == 2  # the "." row is dropped, not read as zero
    assert series.iloc[-1] == pytest.approx(5.90)


def test_fred_rejects_an_unknown_series_name():
    with pytest.raises(DataSourceError, match="inconnue"):
        fred.named("taux_imaginaire")


def test_ecb_sorts_by_period(monkeypatch):
    monkeypatch.setattr(http, "get_text", lambda *a, **k: ECB_CSV)

    series = ecb.named("eur_usd")

    assert list(series.index.strftime("%Y-%m-%d")) == ["2026-09-04", "2026-09-08"]
    assert series.iloc[-1] == pytest.approx(1.1614)


def test_ecb_reports_an_unexpected_payload(monkeypatch):
    monkeypatch.setattr(http, "get_text", lambda *a, **k: "KEY,FREQ\nX,D\n")

    with pytest.raises(DataSourceError, match="inattendue"):
        ecb.named("eur_usd")


def test_eurostat_reads_the_jsonstat_positions(monkeypatch):
    monkeypatch.setattr(http, "get_text", lambda *a, **k: EUROSTAT_JSON)

    assert eurostat.hicp_index().iloc[-1] == pytest.approx(102.5)
    assert eurostat.inflation_yoy() == pytest.approx(0.025)


def test_eurostat_refuses_to_annualize_a_short_history(monkeypatch):
    short = (
        '{"value": {"0": 100.0}, "dimension": {"time": {"category": {"index": {"2026-01": 0}}}}}'
    )
    monkeypatch.setattr(http, "get_text", lambda *a, **k: short)

    with pytest.raises(DataSourceError, match="trop court"):
        eurostat.inflation_yoy()


def test_ken_french_totals_the_market_and_the_risk_free(monkeypatch):
    monkeypatch.setattr(http, "get_bytes", lambda *a, **k: _zip_of(KEN_FRENCH_CSV))

    monthly = ken_french.monthly_returns("equity_world")

    # 0.77 + 0.68 = 1.45 % of total return for July 1990.
    assert monthly.iloc[0] == pytest.approx(0.0145)
    assert len(monthly) == 2  # the -99.99 month is dropped


def test_ken_french_reads_the_annual_block(monkeypatch):
    monkeypatch.setattr(http, "get_bytes", lambda *a, **k: _zip_of(KEN_FRENCH_CSV))

    annual = ken_french.annual_returns("equity_world")

    assert annual.iloc[-1] == pytest.approx(-0.404)


def test_ken_french_compounds_a_window(monkeypatch):
    monkeypatch.setattr(http, "get_bytes", lambda *a, **k: _zip_of(KEN_FRENCH_CSV))

    compounded = ken_french.window_return("equity_world", "1990-07", "1990-08")

    assert compounded == pytest.approx(1.0145 * 0.9061 - 1.0)


def test_ken_french_rejects_an_unknown_region():
    with pytest.raises(DataSourceError, match="Région inconnue"):
        ken_french.monthly_returns("crypto")


LBMA_JSON = """[
  {"d": "1998-12-31", "v": [287.8, 173.0, null]},
  {"d": "2008-01-02", "v": [846.75, 425.0, 576.0]},
  {"d": "2008-12-31", "v": [869.75, 601.0, 621.0]}
]"""


def test_lbma_skips_the_euro_leg_before_the_euro(monkeypatch):
    monkeypatch.setattr(http, "get_text", lambda *a, **k: LBMA_JSON)

    in_euro = lbma.price("gold", "EUR")
    in_dollar = lbma.price("gold", "USD")

    assert len(in_euro) == 2  # the 1998 session has no euro quote
    assert len(in_dollar) == 3
    assert in_euro.iloc[-1] == pytest.approx(621.0)


def test_lbma_computes_a_window_return(monkeypatch):
    monkeypatch.setattr(http, "get_text", lambda *a, **k: LBMA_JSON)

    assert lbma.window_return("gold", "2008-01-01", "2008-12-31") == pytest.approx(621 / 576 - 1)


def test_lbma_rejects_an_unknown_metal_or_currency(monkeypatch):
    monkeypatch.setattr(http, "get_text", lambda *a, **k: LBMA_JSON)

    with pytest.raises(DataSourceError, match="Métal inconnu"):
        lbma.price("platine")
    with pytest.raises(DataSourceError, match="Devise LBMA inconnue"):
        lbma.price("gold", "CHF")


def test_openfigi_maps_an_unknown_isin_to_an_empty_list(monkeypatch):
    answer = [{"data": [{"ticker": "CW8", "exchCode": "FP"}]}, {"warning": "No identifier found."}]
    monkeypatch.setattr(http, "post_json", lambda *a, **k: answer)

    mapped = openfigi.map_isins(["LU1681043599", "XX0000000000"])

    assert mapped["LU1681043599"][0]["ticker"] == "CW8"
    assert mapped["XX0000000000"] == []


def test_openfigi_picks_the_ticker_of_the_requested_venue(monkeypatch):
    answer = [{"data": [{"ticker": "AMEW", "exchCode": "GR"}, {"ticker": "CW8", "exchCode": "FP"}]}]
    monkeypatch.setattr(http, "post_json", lambda *a, **k: answer)

    assert openfigi.ticker_for("LU1681043599", exchange_code="FP") == "CW8"
    assert openfigi.ticker_for("LU1681043599", exchange_code="XX") is None


def test_openfigi_skips_the_call_when_there_is_nothing_to_map():
    assert openfigi.map_isins(["", "  "]) == {}


def test_http_serves_the_second_call_from_the_cache(monkeypatch):
    calls = {"n": 0}

    class _Response:
        text = "observation_date,X\n2026-01-01,1\n"

        def raise_for_status(self):
            return None

    def _fake_request(method, url, **kwargs):
        calls["n"] += 1
        return _Response()

    monkeypatch.setattr(http.httpx, "request", _fake_request)

    http.get_text("https://example.test/series", ttl_hours=1)
    http.get_text("https://example.test/series", ttl_hours=1)

    assert calls["n"] == 1


def test_every_declared_source_has_an_endpoint():
    cfg = config()

    assert cfg.fred.series and cfg.ecb.series and cfg.ken_french.regions
    for url in (cfg.fred.base_url, cfg.ecb.base_url, cfg.eurostat.base_url, cfg.openfigi.base_url):
        assert url.startswith("https://")
