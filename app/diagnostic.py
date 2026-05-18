"""Rule-based diagnostic on portfolio metrics. Returns human-readable insights.

Each rule is a small function `_<rule_name>(metrics, out)` that may append
to `out`. To add a new rule, write a function and register it in `_RULES`.
"""
from .models import Insight, PortfolioMetrics

HIGH_CONCENTRATION = 0.40
HIGH_CORRELATION = 0.85
LOW_SHARPE = 0.30
GOOD_SHARPE = 0.60
HIGH_VOL = 0.20


def generate(m: PortfolioMetrics) -> list[Insight]:
    insights: list[Insight] = []
    for rule in _RULES:
        rule(m, insights)
    return insights


def _concentration(m: PortfolioMetrics, out: list[Insight]) -> None:
    for a in m.assets:
        if a.weight > HIGH_CONCENTRATION:
            out.append(Insight(
                severity="warning",
                title=f"Concentration sur {a.ticker}",
                detail=(
                    f"{a.ticker} pèse {a.weight:.0%} du portefeuille. "
                    f"Au-delà de 40 % un seul actif domine la performance."
                ),
            ))


def _correlation(m: PortfolioMetrics, out: list[Insight]) -> None:
    seen: set[frozenset[str]] = set()
    for a, row in m.correlation.items():
        for b, rho in row.items():
            pair = frozenset([a, b])
            if a == b or pair in seen:
                continue
            seen.add(pair)
            if rho > HIGH_CORRELATION:
                out.append(Insight(
                    severity="warning",
                    title=f"Corrélation forte : {a} ↔ {b}",
                    detail=(
                        f"ρ = {rho:.2f}. Ces actifs bougent ensemble — "
                        f"le gain de diversification est limité."
                    ),
                ))


def _sharpe(m: PortfolioMetrics, out: list[Insight]) -> None:
    if m.sharpe >= GOOD_SHARPE:
        out.append(Insight(
            severity="good",
            title="Rendement/risque correct",
            detail=f"Sharpe = {m.sharpe:.2f}. La volatilité est correctement rémunérée.",
        ))
    elif m.sharpe < LOW_SHARPE:
        out.append(Insight(
            severity="critical",
            title="Sharpe faible",
            detail=(
                f"Sharpe = {m.sharpe:.2f}. Le rendement attendu ne compense "
                f"pas suffisamment la volatilité."
            ),
        ))


def _volatility(m: PortfolioMetrics, out: list[Insight]) -> None:
    if m.volatility > HIGH_VOL:
        out.append(Insight(
            severity="warning",
            title="Volatilité élevée",
            detail=(
                f"σ annualisée = {m.volatility:.0%}. Sur cycle défavorable, "
                f"prévoir des baisses de 30 à 40 %."
            ),
        ))


_RULES = (_concentration, _correlation, _sharpe, _volatility)
