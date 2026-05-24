"""Portfolio analytics — pure functions over price/return series.

No I/O, no domain types. Inputs are pandas/numpy, outputs are primitives.
Annualization uses 252 trading days. Risk-free rate is the module-level constant.
"""

from collections.abc import Callable
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


def annualized_stats(
    returns: pd.DataFrame,
    risk_free: float = RISK_FREE,
    mu_override: dict[str, float] | None = None,
) -> dict[str, AssetStat]:
    """Per-asset annualized mean, volatility, Sharpe.

    If `mu_override` provided, use those μ instead of the historical mean.
    σ is always computed from historical data (CMAs target μ, not σ).
    """
    mu = returns.mean() * TRADING_DAYS
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
    if mu_override:
        mu_per_asset = np.array(
            [mu_override.get(t, returns[t].mean() * TRADING_DAYS) for t in returns.columns]
        )
    else:
        mu_per_asset = returns.mean().values * TRADING_DAYS
    cov = returns.cov().values * TRADING_DAYS
    expected = float(weights @ mu_per_asset)
    vol = float(np.sqrt(weights @ cov @ weights))
    sharpe = (expected - risk_free) / vol if vol > 0 else 0.0
    return PortfolioStat(expected_return=expected, volatility=vol, sharpe=sharpe)


def cvar_95(returns_series: pd.Series) -> float:
    """Conditional VaR à 95 % (Expected Shortfall) — annualisé.

    = moyenne des rendements quotidiens dans le pire 5 %, × √252 pour annualiser
    Plus honnête que VaR car prend la moyenne de la queue, pas juste le seuil.
    Renvoie un nombre négatif (perte attendue dans les pires journées).
    """
    if returns_series.empty:
        return 0.0
    threshold = np.percentile(returns_series.values, 5)  # 5e percentile = seuil VaR
    tail = returns_series[returns_series <= threshold]
    if tail.empty:
        return float(threshold * np.sqrt(TRADING_DAYS))
    return float(tail.mean() * np.sqrt(TRADING_DAYS))


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


def kelly_leverage(
    mu: np.ndarray, cov: np.ndarray, risk_free: float = RISK_FREE
) -> dict[str, float]:
    """Kelly leverage indicator : combien le solveur Kelly théorique investirait
    si la contrainte sum(w)=1 et long-only étaient relâchées.

    Formule : w_kelly = Σ⁻¹ (μ − r_f×1)  ;  leverage = sum(w_kelly)

    Interprétation :
    - leverage > 1 : Kelly suggère du levier (les actifs sont très attractifs ;
      sans levier dispo, l'investissement plein sans cash est rationnel)
    - leverage < 1 : Kelly suggère de garder du cash (risk-reward médiocre)
    - leverage ≈ 1 : fully invested sans levier est juste

    Half-Kelly applique un facteur 0,5 pour gérer l'incertitude sur μ.
    """
    excess = mu - risk_free
    try:
        raw = np.linalg.solve(cov, excess)
    except np.linalg.LinAlgError:
        # Σ singulière → fallback diagonale
        raw = excess / np.maximum(np.diag(cov), 1e-10)
    full_leverage = float(raw.sum())
    return {
        "full_kelly_leverage": full_leverage,
        "half_kelly_leverage": full_leverage / 2,
    }


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
    monthly_fee: "Callable[[float], float] | None" = None,
) -> dict[str, list[float]]:
    """Three deterministic DCA paths: bear (μ-σ), base (μ), bull (μ+σ).

    If `monthly_fee(value) -> €` is supplied, fees are deducted at each month-end
    so they compound (lost money does not grow further).
    """
    fee = monthly_fee or (lambda _v: 0.0)
    paths: dict[str, list[float]] = {}
    for label, mu in (
        ("bear", annual_return - annual_vol),
        ("base", annual_return),
        ("bull", annual_return + annual_vol),
    ):
        rm = (1 + mu) ** (1 / 12) - 1 if mu > -1 else -0.99
        v = initial
        series = [v]
        for _ in range(months):
            v = v * (1 + rm) + monthly_contribution - fee(v)
            series.append(v)
        paths[label] = series
    return paths


def monte_carlo_projection(
    daily_log_returns: pd.Series,
    initial: float,
    monthly_contribution: float,
    months: int,
    monthly_fee: "Callable[[float], float] | None" = None,
    n_paths: int = 1000,
    seed: int = 42,
) -> dict[str, list[float] | np.ndarray]:
    """Parametric Monte Carlo on monthly log-returns derived from daily history.

    Returns percentile bands p10/p25/p50/p75/p90 at each month, plus the
    probability of reaching `goal` at each month if provided via wrapper.
    Fees (if given) deducted per-path per-month and compound correctly.
    """
    if daily_log_returns is None or daily_log_returns.empty:
        raise ValueError("Aucun rendement historique pour la simulation Monte-Carlo.")

    rng = np.random.default_rng(seed)
    days_per_month = TRADING_DAYS / 12  # ≈ 21
    mu = float(daily_log_returns.mean()) * days_per_month
    sigma = float(daily_log_returns.std()) * np.sqrt(days_per_month)

    log_rets = rng.normal(mu, sigma, size=(n_paths, months))
    gross = np.exp(log_rets)

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
    """Common SLSQP body. mu, cov, bounds already finalized (possibly augmented)."""
    from scipy.optimize import minimize

    n = len(mu)
    w0 = np.full(n, 1 / n)
    constraints: list[dict] = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

    if objective == "max_sharpe":

        def fn(w: np.ndarray) -> float:
            vol = float(np.sqrt(w @ cov @ w))
            return -(float(w @ mu) - risk_free) / vol if vol > 1e-10 else 1e6
    elif objective == "min_variance":

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

    res = minimize(
        fn,
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-10, "maxiter": 200},
    )
    w_opt = res.x
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
    objective: str = "max_sharpe",
    risk_free: float = RISK_FREE,
    *,
    envelope_rates: list[float] | None = None,
    envelope_max_weights: list[float] | None = None,
    max_vol: float | None = None,
) -> dict[str, float | list[float]]:
    """Solve via SLSQP for a long-only fully-invested portfolio.

    objective ∈ {"max_sharpe", "min_variance", "target_volatility"}.
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
) -> dict[str, list[float]]:
    """Smooth efficient frontier as N (σ, μ) points from min-variance to max-return.

    Quand mu et cov sont fournis, ils définissent l'univers entier (ETFs seuls ou
    augmenté avec enveloppes). bounds_override permet de plafonner les poids des
    enveloppes par leur headroom (ceilings).
    """
    from scipy.optimize import minimize

    if mu is None:
        mu = returns.mean().values * TRADING_DAYS
    if cov is None:
        cov = returns.cov().values * TRADING_DAYS

    n = len(mu)
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
        return {"vol": [], "ret": [], "sharpe": []}

    mu_min = float(res_minvar.x @ mu)
    mu_max = float(mu.max())

    if mu_max <= mu_min:
        return {"vol": [], "ret": [], "sharpe": []}

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

    return {"vol": vols, "ret": rets, "sharpe": sharpes}


def risk_contributions(returns: pd.DataFrame, weights: np.ndarray) -> dict[str, list[float]]:
    """Euler decomposition: per-asset contribution to portfolio σ. Fractions sum to 1."""
    cov = returns.cov().values * TRADING_DAYS
    vol = float(np.sqrt(weights @ cov @ weights))
    if vol <= 0:
        return {"tickers": list(returns.columns), "fraction": [0.0] * len(weights)}
    marginal = (cov @ weights) / vol  # ∂σ_p/∂w_i
    rc = weights * marginal  # contribution; sums to σ_p
    return {"tickers": list(returns.columns), "fraction": (rc / vol).tolist()}
