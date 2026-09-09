"""The diagnostic must hold for any portfolio, not only for the first user's.

It speaks plain French, names funds rather than tickers, and decides what an
instrument is from what it tracks rather than from a correlation.
"""

import pytest

from app.finance import diagnostic
from app.models import AssetMetrics, Insight, PortfolioMetrics


def _asset(
    ticker: str,
    weight: float,
    label: str | None = None,
    *,
    index_label: str | None = None,
    kind: str = "fund",
    is_diversified: bool = True,
) -> AssetMetrics:
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
        index_label=index_label,
        kind=kind,
        is_diversified=is_diversified,
    )


def _metrics(assets: list[AssetMetrics], sharpe: float = 0.4, vol: float = 0.15):
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
        correlation={a: {b: 1.0 if a == b else 0.3 for b in tickers} for a in tickers},
    )


def _titles(out: list[Insight]) -> str:
    return " | ".join(i.title for i in out)


# ── Doublons ──────────────────────────────────────────────────────────────


def test_three_funds_on_one_index_produce_one_insight_not_three():
    m = _metrics(
        [
            _asset("A", 0.3, "Amundi World", index_label="Actions monde"),
            _asset("B", 0.3, "iShares World", index_label="Actions monde"),
            _asset("C", 0.4, "Lyxor World", index_label="Actions monde"),
        ]
    )

    out = [i for i in diagnostic.generate(m) if "même indice" in i.title]

    assert len(out) == 1
    assert "Amundi World, iShares World et Lyxor World" in out[0].detail
    assert "3 de tes fonds" in out[0].title


def test_funds_on_different_indices_are_not_duplicates():
    m = _metrics(
        [
            _asset("A", 0.5, "Amundi World", index_label="Actions monde"),
            _asset("B", 0.5, "Amundi Nasdaq", index_label="Nasdaq-100", is_diversified=False),
        ]
    )

    assert "même indice" not in _titles(diagnostic.generate(m))


# ── Concentration ─────────────────────────────────────────────────────────


def test_a_single_broad_world_fund_is_never_flagged():
    """Holding one MSCI World tracker is the textbook advice, not a risk."""
    m = _metrics([_asset("CW8", 1.0, "Amundi MSCI World", index_label="Actions monde")])

    assert "pèse" not in _titles(diagnostic.generate(m))


def test_a_single_share_above_the_limit_is_flagged():
    m = _metrics(
        [
            _asset("AI.PA", 0.6, "Air Liquide", kind="stock", is_diversified=False),
            _asset("CW8", 0.4, "Amundi World", index_label="Actions monde"),
        ]
    )

    out = [i for i in diagnostic.generate(m) if "pèse 60 %" in i.title]

    assert len(out) == 1
    assert "une seule société" in out[0].detail


def test_a_sector_fund_above_the_limit_names_its_segment():
    m = _metrics(
        [
            _asset(
                "PUST", 0.7, "Amundi Nasdaq-100", index_label="Nasdaq-100", is_diversified=False
            ),
            _asset("CW8", 0.3, "Amundi World", index_label="Actions monde"),
        ]
    )

    out = [i for i in diagnostic.generate(m) if "pèse 70 %" in i.title]

    assert len(out) == 1
    assert "Nasdaq-100" in out[0].detail


def test_an_unrecognised_heavy_line_says_we_do_not_know():
    m = _metrics([_asset("X", 1.0, "Fonds maison", kind="unknown", is_diversified=False)])

    out = [i for i in diagnostic.generate(m) if "pèse" in i.title]

    assert "on ne sait pas ce qu'il y a dedans" in out[0].detail


# ── Rémunération du risque ────────────────────────────────────────────────


def test_a_century_normal_reward_says_nothing():
    """0.43 is the long-run figure: the old thresholds called it 'ni bon ni mauvais'."""
    m = _metrics([_asset("A", 1.0, index_label="Actions monde")], sharpe=0.43)

    assert all("risque" not in i.title for i in diagnostic.generate(m))


def test_a_clearly_better_reward_is_praised():
    m = _metrics([_asset("A", 1.0, index_label="Actions monde")], sharpe=0.90)

    assert "te paient bien le risque" in _titles(diagnostic.generate(m))


def test_a_clearly_worse_reward_is_flagged():
    m = _metrics([_asset("A", 1.0, index_label="Actions monde")], sharpe=0.05)

    assert "peu de rendement attendu" in _titles(diagnostic.generate(m))


# ── Mauvaise année ────────────────────────────────────────────────────────


def test_the_announced_fall_uses_real_history_when_we_have_it():
    m = _metrics([_asset("A", 1.0, index_label="Actions monde")], vol=0.25)
    ctx = diagnostic.Context(worst_year=-0.469, worst_year_label="Actions monde")

    detail = next(i.detail for i in diagnostic.generate(m, ctx) if "bouger fort" in i.title)

    assert "47 %" in detail
    assert "Actions monde" in detail


def test_the_announced_fall_falls_back_on_volatility_without_history():
    m = _metrics([_asset("A", 1.0)], vol=0.25)

    detail = next(i.detail for i in diagnostic.generate(m) if "bouger fort" in i.title)

    assert "41 %" in detail  # 1,65 × 25 %


def test_a_calm_portfolio_gets_no_fall_warning():
    m = _metrics([_asset("A", 1.0)], vol=0.05)

    assert "bouger fort" not in _titles(diagnostic.generate(m))


# ── Garde-fous généraux ───────────────────────────────────────────────────


def test_the_number_of_insights_is_capped_and_ordered_by_severity():
    assets = [
        _asset(f"F{i}", 0.1, f"Fonds {i}", index_label=f"Indice {i}", is_diversified=False)
        for i in range(10)
    ]
    m = _metrics(assets, sharpe=0.05, vol=0.4)

    out = diagnostic.generate(m)

    assert len(out) <= diagnostic.config().max_insights
    severities = [i.severity for i in out]
    assert severities == sorted(
        severities, key=lambda s: {"critical": 0, "warning": 1, "good": 2}[s]
    )


def test_no_symbols_anywhere():
    m = _metrics(
        [
            _asset("A", 0.5, index_label="Actions monde"),
            _asset("B", 0.5, index_label="Actions monde"),
        ],
        sharpe=0.05,
        vol=0.3,
    )

    text = " ".join(i.title + " " + i.detail for i in diagnostic.generate(m))

    for forbidden in ("σ", "μ", "ρ", "Sharpe", "="):
        assert forbidden not in text, forbidden


def test_a_portfolio_with_nothing_to_say_says_nothing():
    m = _metrics([_asset("A", 1.0, index_label="Actions monde")], sharpe=0.43, vol=0.10)

    assert diagnostic.generate(m) == []


@pytest.mark.parametrize("weight", [0.41, 0.99, 1.0])
def test_the_concentration_rule_does_not_depend_on_the_number_of_lines(weight: float):
    m = _metrics([_asset("X", weight, "Action seule", kind="stock", is_diversified=False)])

    assert "pèse" in _titles(diagnostic.generate(m))
