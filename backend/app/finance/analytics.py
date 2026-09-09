"""Portfolio analytics — pure functions over price/return series.

No I/O, no domain types. Inputs are pandas/numpy, outputs are primitives.
Annualization uses 252 trading days. Risk-free rate is the module-level constant.
"""

from collections.abc import Callable
from typing import TypedDict

import numpy as np
import pandas as pd

TRADING_DAYS = 252
# Fallback only. The observed rate comes from `macro.risk_free_rate()`; this
# module stays pure and takes it as an argument (ADR-026).
RISK_FREE = 0.025


class AssetStat(TypedDict):
    mu: float
    sigma: float
    sharpe: float


class PortfolioStat(TypedDict):
    expected_return: float
    volatility: float
    sharpe: float


class FrontierResult(TypedDict):
    """Return type of efficient_frontier_curve.

    `reason` is None when the frontier was computed successfully, otherwise
    a machine-readable code: "need_two_assets" | "flat_returns" | "solver_failed".
    """

    vol: list[float]
    ret: list[float]
    sharpe: list[float]
    reason: str | None


def daily_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Log returns; first row dropped.

    Raises:
        ValueError: if `prices` is empty or has fewer than 2 observations.
    """
    if prices is None or prices.empty:
        raise ValueError("Aucune donnée de prix.")
    if len(prices) < 2:
        raise ValueError(f"Au moins 2 observations sont nécessaires, reçu {len(prices)}.")
    rets = np.log(prices / prices.shift(1)).dropna()
    if rets.empty:
        raise ValueError("Calcul des rendements impossible (toutes les lignes invalides).")
    return rets


def annualized_arithmetic_mu(returns: pd.DataFrame) -> pd.Series:
    """Annualized *arithmetic* expected return per asset from daily log returns.

    ``mean(log) × 252`` is the geometric drift; mean-variance inputs and the
    CMA figures they are blended with are arithmetic. Under lognormality
    E[R] = exp(m + s²/2) − 1 with m, s the annualized log mean and std.
    """
    m = returns.mean() * TRADING_DAYS
    v = returns.var() * TRADING_DAYS
    return np.exp(m + v / 2) - 1


def annualized_stats(
    returns: pd.DataFrame,
    risk_free: float = RISK_FREE,
    mu_override: dict[str, float] | None = None,
) -> dict[str, AssetStat]:
    """Per-asset annualized mean, volatility, Sharpe.

    If `mu_override` provided, use those μ instead of the historical mean.
    σ is always computed from historical data (CMAs target μ, not σ).
    """
    mu = annualized_arithmetic_mu(returns)
    if mu_override:
        for t in returns.columns:
            if t in mu_override:
                mu[t] = mu_override[t]
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
    mu_override: dict[str, float] | None = None,
) -> PortfolioStat:
    """E(R), σ, Sharpe for weighted portfolio.

    If `mu_override` given, asset μ are overridden before weighting.
    """
    hist_mu = annualized_arithmetic_mu(returns)
    if mu_override:
        mu_per_asset = np.array([mu_override.get(t, float(hist_mu[t])) for t in returns.columns])
    else:
        mu_per_asset = hist_mu.values
    cov = returns.cov().values * TRADING_DAYS
    expected = float(weights @ mu_per_asset)
    vol = float(np.sqrt(weights @ cov @ weights))
    sharpe = (expected - risk_free) / vol if vol > 0 else 0.0
    return PortfolioStat(expected_return=expected, volatility=vol, sharpe=sharpe)


def max_drawdown(price_series: pd.Series) -> float:
    """Plus grande chute peak-to-trough observée. Nombre négatif.

    Calcule l'equity curve cumulative max, puis la dérive max((p − cummax) / cummax).
    """
    if price_series.empty or len(price_series) < 2:
        return 0.0
    series = price_series.dropna()
    if series.empty:
        return 0.0
    cummax = series.cummax()
    drawdown = (series - cummax) / cummax
    return float(drawdown.min())


def shrunk_covariance(returns: pd.DataFrame, shrinkage: float = 0.20) -> np.ndarray:
    """Shrinkage style Ledoit-Wolf simplifié : pull la matrice d'échantillon
    vers une cible diagonale (variance moyenne × I). Stabilise Σ quand l'échantillon
    est court (peu d'historique, fréquent en finance retail).

    shrinkage ∈ [0, 1] : 0 = pure sample, 1 = pure diagonal target.
    """
    cov_sample = returns.cov().values * TRADING_DAYS
    avg_var = float(np.mean(np.diag(cov_sample)))
    target = avg_var * np.eye(cov_sample.shape[0])
    s = max(0.0, min(1.0, shrinkage))
    return s * target + (1 - s) * cov_sample


def correlation_matrix(returns: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Pairwise correlation as nested dict, JSON-friendly."""
    corr = returns.corr()
    return {a: {b: float(corr.loc[a, b]) for b in corr.columns} for a in corr.columns}


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


def _simulate_gross_monthly(
    daily_log_returns: pd.Series,
    months: int,
    n_paths: int,
    seed: int,
    parameter_uncertainty: bool,
) -> np.ndarray:
    """(n_paths, months) matrix of monthly gross returns (1 + r).

    μ̂ and σ̂ come from the daily history rescaled to a month. With
    `parameter_uncertainty` each path draws its own drift from N(μ̂, SE²),
    SE = σ_month / √(months of history): five years of data leave an error on
    μ̂ larger than the dispersion σ alone produces at ten years.

    Shared by the fan chart and the required-contribution solver so both read
    the same simulated futures for a given seed.
    """
    if daily_log_returns is None or daily_log_returns.empty:
        raise ValueError("Aucun rendement historique pour la simulation Monte-Carlo.")
    rng = np.random.default_rng(seed)
    days_per_month = TRADING_DAYS / 12  # ≈ 21
    mu = float(daily_log_returns.mean()) * days_per_month
    sigma = float(daily_log_returns.std()) * np.sqrt(days_per_month)
    if parameter_uncertainty:
        months_of_history = max(len(daily_log_returns) / days_per_month, 1.0)
        se_mu = sigma / np.sqrt(months_of_history)
        mu_paths = rng.normal(mu, se_mu, size=(n_paths, 1))
    else:
        mu_paths = np.full((n_paths, 1), mu)
    return np.exp(rng.normal(mu_paths, sigma, size=(n_paths, months)))


def required_monthly_contribution(
    daily_log_returns: pd.Series,
    initial: float,
    months: int,
    goal: float,
    probability: float,
    *,
    fixed_monthly: float = 0.0,
    proportional_monthly: float = 0.0,
    courtage_pct: float = 0.0,
    n_paths: int = 1000,
    seed: int = 42,
    parameter_uncertainty: bool = True,
) -> float | None:
    """Monthly contribution reaching `goal` with probability `probability`.

    The inverse problem of the projection. On a given path terminal wealth is
    affine in the contribution C, since the broker's fees are a fixed amount
    plus a share of the value and a share of the contribution:

        v(t+1) = v(t)·(g(t) − prop) + C·(1 − courtage) − fixed

    so W = A + C·B and the contribution that path needs is (goal − A)/B. The
    answer is the `probability` quantile of those, exact on the simulated
    paths and without bisection (étude §7.8, point 3).

    `goal` is a nominal amount at the horizon. Returns None when no sane
    contribution reaches it.
    """
    if months <= 0 or goal <= 0 or not 0 < probability < 1:
        return None
    gross = _simulate_gross_monthly(daily_log_returns, months, n_paths, seed, parameter_uncertainty)
    growth = gross - proportional_monthly  # fees are charged on the month's opening value
    a = np.full(gross.shape[0], float(initial))
    b = np.zeros(gross.shape[0])
    per_euro = 1.0 - courtage_pct
    for t in range(months):
        a = a * growth[:, t] - fixed_monthly
        b = b * growth[:, t] + per_euro
    with np.errstate(divide="ignore", invalid="ignore"):
        needed = np.where(b > 0, (goal - a) / b, np.inf)
    value = float(np.quantile(np.maximum(needed, 0.0), probability))
    return value if np.isfinite(value) else None


def monte_carlo_projection(
    daily_log_returns: pd.Series,
    initial: float,
    monthly_contribution: float,
    months: int,
    monthly_fee: "Callable[[float], float] | None" = None,
    n_paths: int = 1000,
    seed: int = 42,
    parameter_uncertainty: bool = True,
) -> dict[str, list[float] | np.ndarray]:
    """Parametric Monte Carlo on monthly log-returns derived from daily history.

    Returns percentile bands p10/p25/p50/p75/p90 at each month, plus the
    probability of reaching `goal` at each month if provided via wrapper.
    Fees (if given) deducted per-path per-month and compound correctly.

    With ``parameter_uncertainty`` each path draws its own drift from
    N(μ̂, SE²), SE = σ_month / √(months of history): with 5 years of data
    SE(μ̂) ≈ 8 %/year for an equity basket, larger than the dispersion the
    return volatility alone produces at a 10-year horizon. A fan drawn from
    σ only is about half as wide as the honest one.
    """
    gross = _simulate_gross_monthly(daily_log_returns, months, n_paths, seed, parameter_uncertainty)

    fee = monthly_fee or (lambda _v: 0.0)

    values = np.empty((n_paths, months + 1), dtype=np.float64)
    values[:, 0] = initial
    for t in range(months):
        next_val = values[:, t] * gross[:, t] + monthly_contribution
        # Apply fees per-path on the pre-fee value
        if monthly_fee is not None:
            next_val = next_val - np.array([fee(v) for v in values[:, t]])
        values[:, t + 1] = next_val

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


def _solve_slsqp(
    mu: np.ndarray,
    cov: np.ndarray,
    bounds: list[tuple[float, float]],
    objective: str,
    risk_free: float,
    max_vol: float | None,
    target_return: float | None = None,
) -> dict[str, float | list[float]]:
    """Common SLSQP body. mu, cov, bounds already finalized (possibly augmented).

    ``from_strategy`` is non-convex: a single start can report a local
    optimum as "optimal". It is solved from several starts
    (equal weight, each vertex, a few Dirichlet draws with a fixed seed) and
    the best converged solution is kept. The result's ``success`` flag is the
    caller's to check: a non-converged solve must never be shown as optimal.
    """
    from scipy.optimize import minimize

    n = len(mu)
    w0 = np.full(n, 1 / n)
    constraints: list[dict] = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

    if objective == "min_variance":

        def fn(w: np.ndarray) -> float:
            return float(w @ cov @ w)
    elif objective == "target_volatility":
        if max_vol is None:
            raise ValueError("target_volatility requires max_vol")

        def fn(w: np.ndarray) -> float:
            return -float(w @ mu)

        constraints.append(
            {
                "type": "ineq",
                "fun": lambda w: float(max_vol) - float(np.sqrt(w @ cov @ w)),
            }
        )
    elif objective == "from_strategy":
        if max_vol is None or target_return is None:
            raise ValueError("from_strategy requires both max_vol and target_return")

        # Maximize Sharpe subject to σ ≤ max_vol AND μ ≥ target_return
        def fn(w: np.ndarray) -> float:
            vol = float(np.sqrt(w @ cov @ w))
            return -(float(w @ mu) - risk_free) / vol if vol > 1e-10 else 1e6

        constraints.append(
            {
                "type": "ineq",
                "fun": lambda w: float(max_vol) - float(np.sqrt(w @ cov @ w)),
            }
        )
        constraints.append(
            {
                "type": "ineq",
                "fun": lambda w: float(w @ mu) - float(target_return),
            }
        )
    else:
        raise ValueError(f"Unknown objective: {objective!r}")

    starts = [w0]
    if objective == "from_strategy":
        starts += [np.eye(n)[i] for i in range(n)]
        starts += list(np.random.default_rng(0).dirichlet(np.ones(n), size=4))

    res = None
    for start in starts:
        cand = minimize(
            fn,
            _project_to_bounds(start, bounds),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-10, "maxiter": 200},
        )
        if res is None or (cand.success and (not res.success or cand.fun < res.fun)):
            res = cand
    assert res is not None
    w_opt = _project_to_bounds(res.x, bounds)
    vol = float(np.sqrt(w_opt @ cov @ w_opt))
    ret = float(w_opt @ mu)
    sharpe = (ret - risk_free) / vol if vol > 1e-10 else 0.0
    return {
        "weights": w_opt.tolist(),
        "expected_return": ret,
        "volatility": vol,
        "sharpe": sharpe,
        "success": bool(res.success),
    }


def _project_to_bounds(w: np.ndarray, bounds: list[tuple[float, float]]) -> np.ndarray:
    """Clip to the box and renormalize to sum 1 (SLSQP can return −1e-9 or 1 ± 1e-9)."""
    lo = np.array([b[0] for b in bounds])
    hi = np.array([b[1] for b in bounds])
    w = np.clip(np.asarray(w, dtype=float), lo, hi)
    total = float(w.sum())
    return w / total if total > 0 else np.full(len(w), 1 / len(w))


def build_asset_stats(
    returns: pd.DataFrame,
    envelope_rates: list[float] | None = None,
    envelope_max_weights: list[float] | None = None,
    sigma_envelope: float = 1e-3,
    mu_override: dict[str, float] | None = None,
    cov_estimator: str = "sample",
    cov_shrinkage: float = 0.20,
) -> tuple[np.ndarray, np.ndarray, list[tuple[float, float]]]:
    """Build (mu, cov, bounds) from historical returns + optional synthetic envelope assets.

    cov_estimator : "sample" (défaut) ou "shrunk" (shrinkage Ledoit-Wolf simplifié).
    cov_shrinkage : fraction de shrinkage si cov_estimator="shrunk", défaut 0.20.
    """
    n = returns.shape[1]
    if mu_override:
        mu = np.array(
            [mu_override.get(t, float(returns[t].mean() * TRADING_DAYS)) for t in returns.columns]
        )
    else:
        mu = returns.mean().values * TRADING_DAYS
    if cov_estimator == "shrunk":
        cov = shrunk_covariance(returns, shrinkage=cov_shrinkage)
    else:
        cov = returns.cov().values * TRADING_DAYS
    bounds: list[tuple[float, float]] = [(0.0, 1.0)] * n

    if envelope_rates:
        assert envelope_max_weights is not None and len(envelope_max_weights) == len(envelope_rates)
        k = len(envelope_rates)
        mu_aug = np.concatenate([mu, np.array(envelope_rates)])
        cov_aug = np.zeros((n + k, n + k))
        cov_aug[:n, :n] = cov
        for i in range(k):
            cov_aug[n + i, n + i] = sigma_envelope**2
        bounds_aug = bounds + [(0.0, max(0.0, min(1.0, mw))) for mw in envelope_max_weights]
        return mu_aug, cov_aug, bounds_aug

    return mu, cov, bounds


def optimize_portfolio(
    returns: pd.DataFrame,
    objective: str = "from_strategy",
    risk_free: float = RISK_FREE,
    *,
    envelope_rates: list[float] | None = None,
    envelope_max_weights: list[float] | None = None,
    max_vol: float | None = None,
) -> dict[str, float | list[float]]:
    """Solve via SLSQP for a long-only fully-invested portfolio.

    objective ∈ {"min_variance", "target_volatility", "from_strategy"}.
    Returns weights aligned with `returns.columns` extended by envelopes if any.
    """
    mu, cov, bounds = build_asset_stats(returns, envelope_rates, envelope_max_weights)
    return _solve_slsqp(mu, cov, bounds, objective, risk_free, max_vol)


def euler_risk_contributions(weights: np.ndarray, cov: np.ndarray) -> list[float]:
    """Generic Euler decomposition for any (weights, cov). Returns fractions summing to 1."""
    vol = float(np.sqrt(weights @ cov @ weights))
    if vol <= 1e-10:
        return [0.0] * len(weights)
    marginal = (cov @ weights) / vol
    rc = weights * marginal
    return (rc / vol).tolist()


def efficient_frontier_curve(
    returns: pd.DataFrame,
    n_points: int = 30,
    risk_free: float = RISK_FREE,
    mu: np.ndarray | None = None,
    cov: np.ndarray | None = None,
    bounds_override: list[tuple[float, float]] | None = None,
) -> FrontierResult:
    """Smooth efficient frontier as N (σ, μ) points from min-variance to max-return.

    Quand mu et cov sont fournis, ils définissent l'univers entier (ETFs seuls ou
    augmenté avec enveloppes). bounds_override permet de plafonner les poids des
    enveloppes par leur headroom (ceilings).

    Returns a FrontierResult: vol/ret/sharpe parallel arrays, plus a machine-readable
    `reason` set to one of "need_two_assets" | "flat_returns" | "solver_failed" when
    the frontier could not be computed; `reason` is None on success.
    """
    from scipy.optimize import minimize

    if mu is None:
        mu = returns.mean().values * TRADING_DAYS
    if cov is None:
        cov = returns.cov().values * TRADING_DAYS

    n = len(mu)
    if n < 2:
        return FrontierResult(vol=[], ret=[], sharpe=[], reason="need_two_assets")

    bounds = bounds_override if bounds_override is not None else [(0.0, 1.0)] * n

    # Min-variance portfolio computed directly avec le cov passé (augmenté ou pas).
    # IMPORTANT : on n'utilise plus optimize_portfolio(returns) ici car ça
    # bypasserait le cov augmenté quand des enveloppes sont dans l'univers.
    res_minvar = minimize(
        lambda w: float(w @ cov @ w),
        np.full(n, 1 / n),
        method="SLSQP",
        bounds=bounds,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
        options={"ftol": 1e-10, "maxiter": 300},
    )
    if not res_minvar.success:
        return FrontierResult(vol=[], ret=[], sharpe=[], reason="solver_failed")

    mu_min = float(res_minvar.x @ mu)
    mu_max = float(mu.max())

    if mu_max <= mu_min:
        return FrontierResult(vol=[], ret=[], sharpe=[], reason="flat_returns")

    targets = np.linspace(mu_min, mu_max, n_points)

    vols: list[float] = []
    rets: list[float] = []
    sharpes: list[float] = []

    for target in targets:
        constraints = [
            {"type": "eq", "fun": lambda w: w.sum() - 1.0},
            {"type": "eq", "fun": lambda w, t=target: float(w @ mu) - t},
        ]
        res = minimize(
            lambda w: float(w @ cov @ w),
            np.full(n, 1 / n),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-10, "maxiter": 300},
        )
        if not res.success:
            continue
        w = res.x
        vol = float(np.sqrt(w @ cov @ w))
        ret = float(w @ mu)
        vols.append(vol)
        rets.append(ret)
        sharpes.append((ret - risk_free) / vol if vol > 0 else 0.0)

    return FrontierResult(vol=vols, ret=rets, sharpe=sharpes, reason=None)


def risk_contributions(returns: pd.DataFrame, weights: np.ndarray) -> dict[str, list[float]]:
    """Euler decomposition: per-asset contribution to portfolio σ. Fractions sum to 1."""
    cov = returns.cov().values * TRADING_DAYS
    vol = float(np.sqrt(weights @ cov @ weights))
    if vol <= 0:
        return {"tickers": list(returns.columns), "fraction": [0.0] * len(weights)}
    marginal = (cov @ weights) / vol  # ∂σ_p/∂w_i
    rc = weights * marginal  # contribution; sums to σ_p
    return {"tickers": list(returns.columns), "fraction": (rc / vol).tolist()}


def worst_rolling_year(monthly_returns: pd.Series) -> float:
    """Worst twelve consecutive months of a monthly return series, as a fraction.

    Used to say what a bad year has actually cost on this asset class, instead
    of deducing it from a normal law that has no fat tails.
    """
    if len(monthly_returns) < 12:
        raise ValueError("Moins de douze mois d'historique.")
    rolling = (1.0 + monthly_returns).rolling(12).apply(np.prod, raw=True) - 1.0
    worst = rolling.min()
    if pd.isna(worst):
        raise ValueError("Aucune fenêtre de douze mois exploitable.")
    return float(worst)
