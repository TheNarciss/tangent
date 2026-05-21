
"""Asset scanner — découverte autonome via yfinance.screen() dynamique.

Architecture :
    1. Construit l'univers par mode (broad_eu / tech_growth / defensive) via
       EquityQuery sur exchange='PAR' (Euronext Paris = quasi tous PEA-éligibles).
    2. Filtre PEA-éligibilité (tickers .PA) + retire les positions déjà détenues.
    3. Pour chaque candidat, calcule ΔSharpe marginal si ajouté à hauteur h %.
       Formule : Sharpe((1-h)·portfolio + h·candidat) − Sharpe(portfolio).
    4. Rank par ΔSharpe descendant, retourne top N.

Cache : univers par mode 24 h (limite quota yfinance).
"""
import logging
import time

import numpy as np
import pandas as pd
import yfinance as yf
from yfinance import EquityQuery

from . import analytics, cma, market
from .. import portfolio
from ..errors import AppError
from ..models import ScanCandidate, ScanRequest, ScanResponse

logger = logging.getLogger(__name__)

# Cache mémoire des univers par mode (timestamp, quotes)
_UNIVERSE_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL_SECONDS = 24 * 3600

# Constructeurs de query par mode. Toutes restreintes à Euronext Paris.
_MODE_BUILDERS: dict[str, callable] = {
    "broad_eu": lambda: EquityQuery("and", [
        EquityQuery("eq", ["exchange", "PAR"]),
        EquityQuery("gt", ["intradaymarketcap", 1_000_000_000]),
    ]),
    "tech_growth": lambda: EquityQuery("and", [
        EquityQuery("eq", ["exchange", "PAR"]),
        EquityQuery("is-in", ["sector", "Technology", "Communication Services"]),
        EquityQuery("gt", ["intradaymarketcap", 500_000_000]),
    ]),
    "defensive": lambda: EquityQuery("and", [
        EquityQuery("eq", ["exchange", "PAR"]),
        EquityQuery("is-in", ["sector", "Utilities", "Consumer Defensive", "Healthcare"]),
        EquityQuery("gt", ["intradaymarketcap", 2_000_000_000]),
    ]),
}


_MODE_LABELS = {
    "broad_eu": "Large cap EU",
    "tech_growth": "Tech / Growth",
    "defensive": "Defensive",
}


def _is_pea_eligible(ticker: str) -> bool:
    """Approximation : tickers Euronext Paris (.PA) = quasi tous PEA-éligibles."""
    return ticker.endswith(".PA")


def _build_universe(modes: list[str], count_per_mode: int = 40) -> list[dict]:
    """Merge des screeners de tous les modes, dédupliqué par symbole. Cache 24 h.

    Tag chaque candidat avec son `_category` (mode d'origine, ou "Multi" si plusieurs).
    """
    now = time.time()
    by_symbol: dict[str, dict] = {}

    for mode in modes:
        if mode not in _MODE_BUILDERS:
            logger.warning("scanner: unknown mode %s", mode)
            continue

        cached = _UNIVERSE_CACHE.get(mode)
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            quotes = cached[1]
            logger.info("scanner: cache hit mode=%s (%d tickers)", mode, len(quotes))
        else:
            try:
                query = _MODE_BUILDERS[mode]()
                result = yf.screen(query, count=count_per_mode)
                quotes = result.get("quotes", []) if isinstance(result, dict) else []
                _UNIVERSE_CACHE[mode] = (now, quotes)
                logger.info("scanner: fetched mode=%s (%d tickers)", mode, len(quotes))
            except Exception as exc:
                logger.error("scanner: failed mode=%s: %s", mode, exc)
                continue

        label = _MODE_LABELS.get(mode, mode)
        for q in quotes:
            sym = q.get("symbol")
            if not sym:
                continue
            if sym in by_symbol:
                # Apparait dans plusieurs modes → "Multi"
                by_symbol[sym]["_category"] = "Multi"
            else:
                q_copy = dict(q)
                q_copy["_category"] = label
                by_symbol[sym] = q_copy

    return list(by_symbol.values())


def _compute_delta_sharpe(
    candidate_returns: pd.Series,
    portfolio_returns: pd.Series,
    mu_c: float,
    p_mu: float, p_sigma: float, p_sharpe: float,
    h: float, risk_free: float,
) -> tuple[float, float, float] | None:
    """Retourne (ΔSharpe, ρ, σ_c) ou None si pas assez de données alignées.

    Calcul :  new_μ = (1−h)·μ_p + h·μ_c
              new_σ² = (1−h)²·σ_p² + h²·σ_c² + 2·h·(1−h)·ρ·σ_p·σ_c
              ΔSharpe = (new_μ − r_f) / new_σ − Sharpe_p
    """
    aligned = pd.concat([candidate_returns, portfolio_returns], axis=1).dropna()
    if len(aligned) < 50:  # min 50 jours communs pour des stats sensées
        return None
    c_ret = aligned.iloc[:, 0]
    p_ret = aligned.iloc[:, 1]

    sigma_c = float(c_ret.std() * np.sqrt(analytics.TRADING_DAYS))
    if sigma_c <= 0:
        return None

    rho = float(c_ret.corr(p_ret))
    if not np.isfinite(rho):
        rho = 0.0

    new_mu = (1 - h) * p_mu + h * mu_c
    new_sigma_sq = (
        (1 - h) ** 2 * p_sigma ** 2
        + h ** 2 * sigma_c ** 2
        + 2 * h * (1 - h) * rho * p_sigma * sigma_c
    )
    new_sigma = float(np.sqrt(max(new_sigma_sq, 1e-12)))
    new_sharpe = (new_mu - risk_free) / new_sigma if new_sigma > 0 else 0.0

    return new_sharpe - p_sharpe, rho, sigma_c


def _rationale(delta: float, rho: float, mu_c: float) -> str:
    """Phrase explicative courte pour l'utilisateur."""
    if delta < 0:
        return f"Dégraderait le Sharpe (ρ={rho:.2f})"
    if abs(rho) < 0.30:
        return f"Excellent diversifier (ρ={rho:.2f}, μ={mu_c*100:.1f} %)"
    if delta > 0.05:
        return f"Booster de Sharpe (+{delta:.2f}) malgré ρ={rho:.2f}"
    return f"Modeste amélioration (ρ={rho:.2f}, μ={mu_c*100:.1f} %)"


def scan(req: ScanRequest) -> ScanResponse:
    start = time.time()

    pf = portfolio.load()
    if not pf.positions:
        raise AppError("Aucune position en portefeuille — impossible de scanner.")

    # Resolve expert settings (mêmes défauts que dashboard)
    expert = req.expert
    period = expert.historical_period if expert and expert.historical_period else "5y"
    rf = expert.risk_free_rate if expert and expert.risk_free_rate is not None else analytics.RISK_FREE
    cma_shrink = expert.cma_shrinkage if expert and expert.cma_shrinkage is not None else None
    cma_overrides = expert.cma_overrides if expert else {}

    # Stats portfolio courant
    pf_tickers = [p.ticker for p in pf.positions]
    prices_p = market.fetch_prices(pf_tickers, period=period)
    returns_p = analytics.daily_log_returns(prices_p[pf_tickers])

    hist_mu_p = (returns_p.mean() * analytics.TRADING_DAYS).values
    blended_p = cma.blended_mu(pf_tickers, hist_mu_p, shrinkage=cma_shrink, overrides=cma_overrides or None)
    mu_override_p = {t: float(blended_p[i]) for i, t in enumerate(pf_tickers)}

    latest = {t: float(prices_p[t].dropna().iloc[-1]) for t in pf_tickers}
    values = np.array([p.quantity * latest[p.ticker] for p in pf.positions])
    weights = values / float(values.sum())

    pf_stats = analytics.portfolio_stats(returns_p, weights, risk_free=rf, mu_override=mu_override_p)
    p_mu, p_sigma, p_sharpe = pf_stats["expected_return"], pf_stats["volatility"], pf_stats["sharpe"]
    portfolio_returns = returns_p @ weights

    # Construire l'univers
    raw = _build_universe(req.modes)
    in_portfolio = set(pf_tickers)
    candidates = [
        c for c in raw
        if c.get("symbol")
        and _is_pea_eligible(c["symbol"])
        and c["symbol"] not in in_portfolio
    ]
    if not candidates:
        return ScanResponse(
            candidates=[], universe_size=len(raw),
            modes_used=req.modes, elapsed_seconds=time.time() - start,
        )

    # Batch fetch des prix
    cand_tickers = [c["symbol"] for c in candidates]
    try:
        prices_c = market.fetch_prices(cand_tickers, period=period)
    except Exception as exc:
        logger.error("scanner: batch fetch failed: %s", exc)
        return ScanResponse(
            candidates=[], universe_size=len(raw),
            modes_used=req.modes, elapsed_seconds=time.time() - start,
        )

    # Compute ΔSharpe par candidat
    h = req.hypothesis_fraction
    scored: list[dict] = []
    for c in candidates:
        sym = c["symbol"]
        if sym not in prices_c.columns:
            continue
        prices_series = prices_c[sym].dropna()
        if len(prices_series) < 50:
            continue

        try:
            cand_returns = analytics.daily_log_returns(prices_series.to_frame()).iloc[:, 0]
        except Exception:
            continue

        # μ blendé pour ce candidat (respect override expert si présent)
        try:
            hist_mu_c = float(cand_returns.mean() * analytics.TRADING_DAYS)
            sym_override = {sym: cma_overrides[sym]} if sym in cma_overrides else {}
            blended_c = cma.blended_mu([sym], np.array([hist_mu_c]),
                                        shrinkage=cma_shrink,
                                        overrides=sym_override or None)
            mu_c = float(blended_c[0])
        except Exception:
            continue

        result = _compute_delta_sharpe(
            cand_returns, portfolio_returns, mu_c,
            p_mu, p_sigma, p_sharpe, h, rf,
        )
        if result is None:
            continue
        delta, rho, sigma_c = result

        own_sharpe = (mu_c - rf) / sigma_c if sigma_c > 0 else 0.0
        scored.append({
            "ticker": sym,
            "name": c.get("shortName") or c.get("longName") or sym,
            "sector": c.get("_category", "N/A"),
            "market_cap": float(c.get("marketCap") or 0),
            "own_mu": mu_c,
            "own_sigma": sigma_c,
            "own_sharpe": own_sharpe,
            "correlation_with_portfolio": rho,
            "delta_sharpe": delta,
            "pea_eligible": True,
            "rationale": _rationale(delta, rho, mu_c),
        })

    # Top N par ΔSharpe descendant
    scored.sort(key=lambda x: x["delta_sharpe"], reverse=True)
    top = scored[: req.n_results]

    elapsed = time.time() - start
    logger.info("scanner: %d/%d candidats retournés, %.1fs", len(top), len(scored), elapsed)

    return ScanResponse(
        candidates=[ScanCandidate(**c) for c in top],
        universe_size=len(raw),
        modes_used=req.modes,
        elapsed_seconds=elapsed,
    )