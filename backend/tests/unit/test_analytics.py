"""Unit tests for pure finance functions (no DB, no I/O)."""

import numpy as np
import pandas as pd
import pytest

from app.finance import analytics


def test_max_drawdown_zero_for_monotonic_series():
    """A strictly increasing series has 0 drawdown."""
    series = pd.Series([100, 110, 120, 130, 140])
    result = analytics.max_drawdown(series)
    assert result == 0.0


def test_efficient_frontier_includes_risk_free_kink():
    """Frontier with a 0-σ asset must extend down to σ=0 + start from μ_rf."""
    import pandas as pd

    rng = np.random.default_rng(42)
    rets = pd.DataFrame(rng.normal(0.0004, 0.012, (252, 2)), columns=["A", "B"])
    mu = np.array([0.08, 0.10, 0.03])  # 2 ETFs + livret @ 3%
    cov = np.diag([0.04, 0.05, 1e-9])  # σ_livret ≈ 0
    bounds = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0)]  # livret uncapped → frontier reaches σ≈0
    f = analytics.efficient_frontier_curve(rets, mu=mu, cov=cov, bounds_override=bounds)
    assert f["vol"], "frontier should not be empty"
    assert min(f["vol"]) < 0.01, "frontier must touch σ≈0 thanks to livret"
    assert min(f["ret"]) >= 0.029, "frontier μ_min ≈ μ_rf (3%)"


def test_max_drawdown_negative_for_crashing_series():
    """A peak-then-crash returns the magnitude of the crash (negative)."""
    series = pd.Series([100, 150, 90, 95])
    result = analytics.max_drawdown(series)
    # crash: peak=150 → trough=90 → -40%
    assert result == pytest.approx(-0.40, abs=0.01)


def test_max_drawdown_empty_series_returns_zero():
    """Empty input returns 0 (not NaN, not raise)."""
    result = analytics.max_drawdown(pd.Series([], dtype=float))
    assert result == 0.0


# ── portfolio_value_series ──────────────────────────────────────────────────


def test_portfolio_value_single_asset_scales_linearly():
    """For 1 ticker with qty=10, the portfolio value at each date = 10 × price."""
    prices = pd.DataFrame({"AAA": [100.0, 110.0, 120.0]})
    result = analytics.portfolio_value_series(prices, {"AAA": 10.0})
    assert list(result) == [1000.0, 1100.0, 1200.0]


def test_portfolio_value_aggregates_multiple_tickers():
    """For 2 tickers, value = qty_1 × price_1 + qty_2 × price_2 at each date."""
    prices = pd.DataFrame({"AAA": [100.0, 110.0], "BBB": [50.0, 60.0]})
    result = analytics.portfolio_value_series(prices, {"AAA": 1.0, "BBB": 2.0})
    # date 0: 1×100 + 2×50 = 200 ; date 1: 1×110 + 2×60 = 230
    assert list(result) == [200.0, 230.0]


# ── normalize ───────────────────────────────────────────────────────────────


def test_normalize_rebases_to_100():
    """normalize([50, 100, 150], base=100) → [100, 200, 300]."""
    result = analytics.normalize(pd.Series([50.0, 100.0, 150.0]), base=100.0)
    assert list(result) == [100.0, 200.0, 300.0]


def test_normalize_default_base_is_100():
    """Default base is 100; first value becomes 100."""
    result = analytics.normalize(pd.Series([200.0, 400.0]))
    assert result.iloc[0] == 100.0
    assert result.iloc[1] == 200.0


# ── daily_log_returns ───────────────────────────────────────────────────────


def test_log_returns_drops_first_nan_row():
    """The first row is dropped (no return possible without a prior price)."""
    prices = pd.DataFrame({"AAA": [100.0, 110.0, 121.0]})
    result = analytics.daily_log_returns(prices)
    # Two returns: ln(110/100) ≈ 0.0953, ln(121/110) ≈ 0.0953
    assert len(result) == 2
    assert result["AAA"].iloc[0] == pytest.approx(np.log(110 / 100), abs=1e-9)


def test_log_returns_zero_for_flat_series():
    """A flat price series produces zero log returns."""
    prices = pd.DataFrame({"AAA": [100.0, 100.0, 100.0]})
    result = analytics.daily_log_returns(prices)
    assert all(result["AAA"] == 0.0)


# ── efficient_frontier_curve: edge cases with unavailable reason ─────────────


def test_frontier_returns_need_two_assets_when_single_asset():
    """A single-asset universe cannot have an efficient frontier — must flag it."""
    rng = np.random.default_rng(7)
    rets = pd.DataFrame(rng.normal(0.0004, 0.012, (252, 1)), columns=["ONLY"])
    mu = np.array([0.08])
    cov = np.array([[0.04]])
    out = analytics.efficient_frontier_curve(rets, mu=mu, cov=cov)
    assert out["vol"] == []
    assert out["ret"] == []
    assert out["reason"] == "need_two_assets"


def test_frontier_returns_flat_returns_when_all_mu_equal():
    """When all assets share the same expected return, frontier is degenerate."""
    rng = np.random.default_rng(11)
    rets = pd.DataFrame(rng.normal(0.0004, 0.012, (252, 2)), columns=["A", "B"])
    mu = np.array([0.05, 0.05])
    cov = np.array([[0.04, 0.0], [0.0, 0.06]])
    out = analytics.efficient_frontier_curve(rets, mu=mu, cov=cov)
    assert out["vol"] == []
    assert out["reason"] == "flat_returns"


def test_frontier_has_no_reason_when_well_posed():
    """A normal 2-asset universe yields a non-empty frontier with reason=None."""
    rng = np.random.default_rng(13)
    rets = pd.DataFrame(rng.normal(0.0004, 0.012, (252, 2)), columns=["A", "B"])
    mu = np.array([0.06, 0.10])
    cov = np.array([[0.04, 0.01], [0.01, 0.06]])
    out = analytics.efficient_frontier_curve(rets, mu=mu, cov=cov, n_points=10)
    assert len(out["vol"]) > 0
    assert out["reason"] is None


def _three_assets():
    mu = np.array([0.04, 0.07, 0.09])
    cov = np.array([[0.0025, 0.001, 0.0005], [0.001, 0.0225, 0.012], [0.0005, 0.012, 0.04]])
    return mu, cov, [(0.0, 1.0)] * 3


@pytest.mark.parametrize("objective", ["min_variance", "target_volatility"])
def test_solve_slsqp_converges_on_well_posed_problem(objective):
    mu, cov, bounds = _three_assets()
    res = analytics._solve_slsqp(mu, cov, bounds, objective, 0.02, 0.10)
    w = np.array(res["weights"])
    assert res["success"] is True
    assert w.min() >= 0.0
    assert w.sum() == pytest.approx(1.0)


def test_solve_slsqp_from_strategy_reports_infeasible_as_failure():
    mu, cov, bounds = _three_assets()
    res = analytics._solve_slsqp(mu, cov, bounds, "from_strategy", 0.02, 0.03, 0.15)
    assert res["success"] is False


def test_from_strategy_multistart_is_not_worse_than_the_equal_weight_start():
    """A non-convex objective solved from one start can report a local optimum."""
    mu, cov, bounds = _three_assets()
    res = analytics._solve_slsqp(mu, cov, bounds, "from_strategy", 0.02, 0.20, target_return=0.06)
    assert res["success"]
    w = np.asarray(res["weights"])
    assert w.min() >= -1e-6 and abs(w.sum() - 1) < 1e-6


def test_the_max_sharpe_objective_is_gone():
    """§8.3: it saturates the highest-ratio asset, and the default did too."""
    with pytest.raises(ValueError, match="Unknown objective"):
        mu, cov, bounds = _three_assets()
        analytics._solve_slsqp(mu, cov, bounds, "max_sharpe", 0.02, None)


def test_annualized_arithmetic_mu_adds_half_variance():
    """E[R] = exp(m + s²/2) − 1 on annualized log stats, not m alone."""
    rng = np.random.default_rng(1)
    rets = pd.DataFrame({"A": rng.normal(0.0003, 0.01, 2520)})
    m = float(rets["A"].mean() * analytics.TRADING_DAYS)
    v = float(rets["A"].var() * analytics.TRADING_DAYS)
    got = float(analytics.annualized_arithmetic_mu(rets)["A"])
    assert got == pytest.approx(np.exp(m + v / 2) - 1)
    assert got > m


def _daily_history(years: int = 5) -> pd.Series:
    rng = np.random.default_rng(7)
    return pd.Series(rng.normal(0.0003, 0.011, years * analytics.TRADING_DAYS))


def test_monte_carlo_parameter_uncertainty_widens_the_fan_not_the_median():
    """Uncertainty on μ̂ (5 years of data) must show up in the band, not in the center."""
    hist = _daily_history(5)
    with_unc = analytics.monte_carlo_projection(hist, 10_000, 500, 120, n_paths=4000)
    without = analytics.monte_carlo_projection(
        hist, 10_000, 500, 120, n_paths=4000, parameter_uncertainty=False
    )
    width_with = with_unc["p90"][-1] - with_unc["p10"][-1]
    width_without = without["p90"][-1] - without["p10"][-1]
    assert width_with > 1.3 * width_without
    assert with_unc["p50"][-1] == pytest.approx(without["p50"][-1], rel=0.05)


def test_monte_carlo_uncertainty_shrinks_with_longer_history():
    """Same μ̂ and σ̂, ten times more observations: SE(μ̂) falls by √10, the fan narrows."""
    short = _daily_history(2)
    long = pd.concat([short] * 10, ignore_index=True)
    fan_short = analytics.monte_carlo_projection(short, 10_000, 500, 120, n_paths=4000)
    fan_long = analytics.monte_carlo_projection(long, 10_000, 500, 120, n_paths=4000)
    assert (fan_short["p90"][-1] - fan_short["p10"][-1]) > (
        fan_long["p90"][-1] - fan_long["p10"][-1]
    )


# ── Inverse problem: the contribution a goal requires ──────────────────────


def _flat_returns(mu_daily: float = 0.0003, sigma_daily: float = 0.008) -> pd.Series:
    rng = np.random.default_rng(3)
    return pd.Series(rng.normal(mu_daily, sigma_daily, 1260))


def test_required_contribution_reaches_the_asked_probability():
    """The answer, replayed on the same paths, hits the target probability."""
    rets = _flat_returns()
    required = analytics.required_monthly_contribution(
        rets, initial=5_000.0, months=120, goal=60_000.0, probability=0.75, seed=11
    )
    assert required is not None
    mc = analytics.monte_carlo_projection(rets, 5_000.0, required, 120, n_paths=1000, seed=11)
    reached = analytics.goal_probability(np.asarray(mc["_paths"]), 60_000.0)[-1]
    assert reached == pytest.approx(0.75, abs=0.02)


def test_required_contribution_grows_with_the_probability():
    rets = _flat_returns()
    args = dict(initial=0.0, months=120, goal=50_000.0, seed=5)
    p50 = analytics.required_monthly_contribution(rets, probability=0.50, **args)
    p75 = analytics.required_monthly_contribution(rets, probability=0.75, **args)
    p90 = analytics.required_monthly_contribution(rets, probability=0.90, **args)
    assert p50 is not None and p75 is not None and p90 is not None
    assert p50 < p75 < p90


def test_required_contribution_is_zero_when_the_capital_already_gets_there():
    rets = _flat_returns()
    required = analytics.required_monthly_contribution(
        rets, initial=100_000.0, months=120, goal=1_000.0, probability=0.75, seed=5
    )
    assert required == 0.0


def test_required_contribution_accounts_for_fees():
    """Fees raise the contribution needed for the same goal."""
    rets = _flat_returns()
    args = dict(initial=0.0, months=120, goal=50_000.0, probability=0.75, seed=7)
    free = analytics.required_monthly_contribution(rets, **args)
    charged = analytics.required_monthly_contribution(
        rets, fixed_monthly=5.0, proportional_monthly=0.004 / 12, courtage_pct=0.005, **args
    )
    assert free is not None and charged is not None
    assert charged > free


def test_required_contribution_rejects_a_meaningless_ask():
    rets = _flat_returns()
    assert analytics.required_monthly_contribution(rets, 0.0, 0, 1000.0, 0.75) is None
    assert analytics.required_monthly_contribution(rets, 0.0, 120, 0.0, 0.75) is None
