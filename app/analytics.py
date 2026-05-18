"""Portfolio analytics — pure functions over price/return series.

No I/O, no domain types. Inputs are pandas/numpy, outputs are primitives.
Annualization uses 252 trading days. Risk-free rate is the module-level constant.
"""
from typing import TypedDict

import numpy as np
import pandas as pd

TRADING_DAYS = 252
RISK_FREE = 0.025  # ECB deposit rate, override at call site if needed


class AssetStat(TypedDict):
    mu: float
    sigma: float
    sharpe: float


class PortfolioStat(TypedDict):
    expected_return: float
    volatility: float
    sharpe: float


def daily_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Log returns; first row dropped."""
    return np.log(prices / prices.shift(1)).dropna()


def annualized_stats(returns: pd.DataFrame, risk_free: float = RISK_FREE) -> dict[str, AssetStat]:
    """Per-asset annualized mean, volatility, Sharpe."""
    mu = returns.mean() * TRADING_DAYS
    sigma = returns.std() * np.sqrt(TRADING_DAYS)
    sharpe = (mu - risk_free) / sigma
    return {
        a: AssetStat(mu=float(mu[a]), sigma=float(sigma[a]), sharpe=float(sharpe[a]))
        for a in returns.columns
    }


def portfolio_stats(
    returns: pd.DataFrame,
    weights: np.ndarray,
    risk_free: float = RISK_FREE,
) -> PortfolioStat:
    """E(R), σ, Sharpe for weighted portfolio. Weights aligned with `returns.columns`."""
    mu = returns.mean().values * TRADING_DAYS
    cov = returns.cov().values * TRADING_DAYS
    expected = float(weights @ mu)
    vol = float(np.sqrt(weights @ cov @ weights))
    sharpe = (expected - risk_free) / vol if vol > 0 else 0.0
    return PortfolioStat(expected_return=expected, volatility=vol, sharpe=sharpe)


def correlation_matrix(returns: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Pairwise correlation as nested dict, JSON-friendly."""
    corr = returns.corr()
    return {a: {b: float(corr.loc[a, b]) for b in corr.columns} for a in corr.columns}


def efficient_frontier_cloud(
    returns: pd.DataFrame,
    n: int = 3000,
    seed: int = 42,
) -> dict[str, list[float]]:
    """Sample `n` random long-only fully-invested portfolios on the simplex.

    Returns parallel arrays `vol`, `ret` (annualized) and `sharpe`. The upper-left
    envelope of the cloud traces the efficient frontier.
    """
    rng = np.random.default_rng(seed)
    mu = returns.mean().values * TRADING_DAYS
    cov = returns.cov().values * TRADING_DAYS
    w = rng.dirichlet(np.ones(returns.shape[1]), n)
    ret = w @ mu
    vol = np.sqrt(np.einsum("ij,jk,ik->i", w, cov, w))
    sharpe = (ret - RISK_FREE) / np.where(vol > 0, vol, np.nan)
    return {"vol": vol.tolist(), "ret": ret.tolist(), "sharpe": np.nan_to_num(sharpe).tolist()}


def portfolio_value_series(prices: pd.DataFrame, quantities: dict[str, float]) -> pd.Series:
    """Σ qty_i × price_i(t) — value of holding `quantities` from start to now.

    Caveat: this assumes positions held constant throughout. With a DCA strategy
    that is counterfactual ("as-if-held"); useful for trends, drawdown and rolling
    Sharpe but not for true PnL tracking (would need a transaction log).
    """
    return sum(prices[t] * q for t, q in quantities.items()).dropna()


def normalize(series: pd.Series, base: float = 100.0) -> pd.Series:
    """Rebase a series so its first observation equals `base`."""
    return series / series.iloc[0] * base


def drawdown_series(values: pd.Series) -> pd.Series:
    """Drawdown from running maximum, as a non-positive fraction."""
    running_max = values.cummax()
    return (values - running_max) / running_max


def rolling_sharpe(
    returns: pd.Series,
    window: int = 126,
    risk_free: float = RISK_FREE,
) -> pd.Series:
    """Rolling Sharpe over `window` trading days (126 ≈ 6 months).

    First `window` observations are NaN by construction.
    """
    excess_daily = returns - risk_free / TRADING_DAYS
    mu = excess_daily.rolling(window).mean() * TRADING_DAYS
    sigma = returns.rolling(window).std() * np.sqrt(TRADING_DAYS)
    return mu / sigma


# ─── DCA projection ────────────────────────────────────────────────────────


def deterministic_projection(
    initial: float,
    monthly_contribution: float,
    annual_return: float,
    annual_vol: float,
    months: int,
) -> dict[str, list[float]]:
    """Three deterministic DCA paths: bear (μ-σ), base (μ), bull (μ+σ)."""
    paths: dict[str, list[float]] = {}
    for label, mu in (("bear", annual_return - annual_vol),
                       ("base", annual_return),
                       ("bull", annual_return + annual_vol)):
        rm = (1 + mu) ** (1 / 12) - 1 if mu > -1 else -0.99
        v = initial
        series = [v]
        for _ in range(months):
            v = v * (1 + rm) + monthly_contribution
            series.append(v)
        paths[label] = series
    return paths


def monte_carlo_projection(
    daily_log_returns: pd.Series,
    initial: float,
    monthly_contribution: float,
    months: int,
    n_paths: int = 1000,
    seed: int = 42,
) -> dict[str, list[float]]:
    """Parametric Monte Carlo on monthly log-returns derived from daily history.

    Returns percentile bands p10/p25/p50/p75/p90 at each month, plus the
    probability of reaching `goal` at each month if provided via wrapper.
    """
    rng = np.random.default_rng(seed)
    days_per_month = TRADING_DAYS / 12  # ≈ 21
    mu = float(daily_log_returns.mean()) * days_per_month
    sigma = float(daily_log_returns.std()) * np.sqrt(days_per_month)

    log_rets = rng.normal(mu, sigma, size=(n_paths, months))
    gross = np.exp(log_rets)

    values = np.empty((n_paths, months + 1), dtype=np.float64)
    values[:, 0] = initial
    for t in range(months):
        values[:, t + 1] = values[:, t] * gross[:, t] + monthly_contribution

    bands = np.percentile(values, [10, 25, 50, 75, 90], axis=0)
    return {
        "p10": bands[0].tolist(),
        "p25": bands[1].tolist(),
        "p50": bands[2].tolist(),
        "p75": bands[3].tolist(),
        "p90": bands[4].tolist(),
        "_paths": values,  # kept for goal probability; orchestrator strips this
    }


def goal_probability(paths: np.ndarray, goal: float) -> list[float]:
    """At each column (month), fraction of paths whose value ≥ goal."""
    return (paths >= goal).mean(axis=0).tolist()


# ─── Portfolio optimization ────────────────────────────────────────────────


def optimize_portfolio(
    returns: pd.DataFrame,
    objective: str = "max_sharpe",
    risk_free: float = RISK_FREE,
) -> dict[str, float | list[float]]:
    """Solve via SLSQP for a long-only fully-invested portfolio.

    objective ∈ {"max_sharpe", "min_variance"}.
    Returns weights aligned with `returns.columns` plus expected_return/volatility/sharpe.
    """
    from scipy.optimize import minimize  # lazy import to keep cold-start cheap

    n = returns.shape[1]
    mu = returns.mean().values * TRADING_DAYS
    cov = returns.cov().values * TRADING_DAYS

    def neg_sharpe(w: np.ndarray) -> float:
        vol = float(np.sqrt(w @ cov @ w))
        return -(float(w @ mu) - risk_free) / vol if vol > 0 else 1e6

    def variance(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    fn = {"max_sharpe": neg_sharpe, "min_variance": variance}.get(objective)
    if fn is None:
        raise ValueError(f"Unknown objective: {objective!r}")

    w0 = np.full(n, 1 / n)
    bounds = [(0.0, 1.0)] * n
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

    res = minimize(fn, w0, method="SLSQP", bounds=bounds, constraints=constraints,
                   options={"ftol": 1e-10, "maxiter": 200})

    w_opt = res.x
    vol = float(np.sqrt(w_opt @ cov @ w_opt))
    ret = float(w_opt @ mu)
    sharpe = (ret - risk_free) / vol if vol > 0 else 0.0
    return {
        "weights": w_opt.tolist(),
        "expected_return": ret,
        "volatility": vol,
        "sharpe": sharpe,
    }


def efficient_frontier_curve(
    returns: pd.DataFrame,
    n_points: int = 30,
    risk_free: float = RISK_FREE,
) -> dict[str, list[float]]:
    """Smooth efficient frontier as N (σ, μ) points from min-variance to max-return."""
    from scipy.optimize import minimize

    n = returns.shape[1]
    mu = returns.mean().values * TRADING_DAYS
    cov = returns.cov().values * TRADING_DAYS

    # Endpoints: μ at the min-variance portfolio (lower bound) and the single max-μ asset (upper bound)
    min_var = optimize_portfolio(returns, "min_variance", risk_free)
    mu_min = float(min_var["expected_return"])
    mu_max = float(mu.max())

    if mu_max <= mu_min:
        return {"vol": [], "ret": [], "sharpe": []}

    targets = np.linspace(mu_min, mu_max, n_points)
    bounds = [(0.0, 1.0)] * n

    vols: list[float] = []
    rets: list[float] = []
    sharpes: list[float] = []

    for target in targets:
        constraints = [
            {"type": "eq", "fun": lambda w: w.sum() - 1.0},
            {"type": "eq", "fun": lambda w, t=target: float(w @ mu) - t},
        ]
        res = minimize(lambda w: float(w @ cov @ w), np.full(n, 1 / n),
                       method="SLSQP", bounds=bounds, constraints=constraints,
                       options={"ftol": 1e-10, "maxiter": 200})
        if not res.success:
            continue
        w = res.x
        vol = float(np.sqrt(w @ cov @ w))
        ret = float(w @ mu)
        vols.append(vol)
        rets.append(ret)
        sharpes.append((ret - risk_free) / vol if vol > 0 else 0.0)

    return {"vol": vols, "ret": rets, "sharpe": sharpes}


def risk_contributions(returns: pd.DataFrame, weights: np.ndarray) -> dict[str, list[float]]:
    """Euler decomposition: per-asset contribution to portfolio σ. Fractions sum to 1."""
    cov = returns.cov().values * TRADING_DAYS
    vol = float(np.sqrt(weights @ cov @ weights))
    if vol <= 0:
        return {"tickers": list(returns.columns), "fraction": [0.0] * len(weights)}
    marginal = (cov @ weights) / vol             # ∂σ_p/∂w_i
    rc = weights * marginal                       # contribution; sums to σ_p
    return {"tickers": list(returns.columns), "fraction": (rc / vol).tolist()}