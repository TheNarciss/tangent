"""Unit tests: the diagnostic speaks plain French and names funds, not tickers."""

from app.finance import diagnostic
from app.models import AssetMetrics, PortfolioMetrics


def _asset(ticker: str, weight: float, label: str | None = None) -> AssetMetrics:
    return AssetMetrics(
        ticker=ticker,
        label=label,
        price=100.0,
        weight=weight,
        value=weight * 1000,
        pnl=0.0,
        pnl_pct=0.0,
        annual_return=0.07,
        annual_vol=0.15,
        sharpe=0.4,
    )


def _metrics(assets: list[AssetMetrics], rho: float = 0.3, sharpe: float = 0.4, vol: float = 0.15):
    tickers = [a.ticker for a in assets]
    return PortfolioMetrics(
        total_value=1000.0,
        total_cost=900.0,
        total_pnl=100.0,
        total_pnl_pct=0.11,
        expected_return=0.07,
        volatility=vol,
        sharpe=sharpe,
        assets=assets,
        correlation={a: {b: 1.0 if a == b else rho for b in tickers} for a in tickers},
    )


def test_concentration_uses_the_fund_name_and_a_hint():
    m = _metrics([_asset("CW8.PA", 0.6, "Amundi MSCI World"), _asset("PUST.PA", 0.4)])
    out = diagnostic.generate(m)
    concentration = [i for i in out if "pèse 60 %" in i.title]
    assert len(concentration) == 1
    assert "Amundi MSCI World" in concentration[0].detail
    assert "Piste" in concentration[0].detail
    assert "σ" not in concentration[0].detail and "Sharpe" not in concentration[0].detail


def test_correlation_names_both_funds_as_a_duplicate():
    m = _metrics([_asset("A", 0.5, "Fonds A"), _asset("B", 0.5, "Fonds B")], rho=0.9)
    titles = [i.title for i in diagnostic.generate(m)]
    assert "Fonds A et Fonds B font doublon" in titles


def test_no_symbols_anywhere():
    m = _metrics([_asset("A", 0.5), _asset("B", 0.5)], rho=0.9, sharpe=0.1, vol=0.3)
    text = " ".join(i.title + " " + i.detail for i in diagnostic.generate(m))
    for forbidden in ("σ", "μ", "ρ", "Sharpe", "="):
        assert forbidden not in text, forbidden
