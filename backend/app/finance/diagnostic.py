"""Rule-based diagnostic on portfolio metrics, written for a non-expert.

Each insight is one plain sentence about what is going on and, when useful,
one "Piste :" (a hint) the reader can act on. No Greek letters, no ratios.

Each rule is a small function `_<rule_name>(metrics, out)` that may append
to `out`. To add a new rule, write a function and register it in `_RULES`.
Thresholds are unchanged business values.
"""

from ..models import AssetMetrics, Insight, PortfolioMetrics

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


def _pct(x: float) -> str:
    """French percent: 60 % (space before the sign)."""
    return f"{x * 100:.0f} %"


def _name(a: AssetMetrics) -> str:
    return a.label or a.ticker


def _name_of(m: PortfolioMetrics, ticker: str) -> str:
    for a in m.assets:
        if a.ticker == ticker:
            return _name(a)
    return ticker


def _concentration(m: PortfolioMetrics, out: list[Insight]) -> None:
    for a in m.assets:
        if a.weight > HIGH_CONCENTRATION:
            out.append(
                Insight(
                    severity="warning",
                    title=f"Une seule ligne pèse {_pct(a.weight)} de tes placements",
                    detail=(
                        f"{_name(a)} fait à lui seul {_pct(a.weight)} du total : ses hausses et "
                        f"ses baisses décident de presque toute ta performance. "
                        f"Piste : diriger les prochains versements vers tes autres lignes."
                    ),
                )
            )


def _correlation(m: PortfolioMetrics, out: list[Insight]) -> None:
    seen: set[frozenset[str]] = set()
    for a, row in m.correlation.items():
        for b, rho in row.items():
            pair = frozenset([a, b])
            if a == b or pair in seen:
                continue
            seen.add(pair)
            if rho > HIGH_CORRELATION:
                out.append(
                    Insight(
                        severity="warning",
                        title=f"{_name_of(m, a)} et {_name_of(m, b)} font doublon",
                        detail=(
                            "Ces deux fonds montent et baissent presque toujours ensemble : "
                            "en garder deux ne te protège pas plus qu'un seul. "
                            "Piste : concentrer les versements sur l'un des deux."
                        ),
                    )
                )


def _sharpe(m: PortfolioMetrics, out: list[Insight]) -> None:
    if m.sharpe >= GOOD_SHARPE:
        out.append(
            Insight(
                severity="good",
                title="Ton risque est bien rémunéré",
                detail=(
                    "Le rendement attendu de tes placements est à la hauteur des variations "
                    "que tu acceptes. Rien à changer de ce côté."
                ),
            )
        )
    elif m.sharpe < LOW_SHARPE:
        out.append(
            Insight(
                severity="critical",
                title="Beaucoup de variations pour peu de rendement attendu",
                detail=(
                    "Tes placements peuvent bouger fort sans que le rendement espéré le "
                    "justifie. Piste : regarder la proposition ci-dessous."
                ),
            )
        )


def _volatility(m: PortfolioMetrics, out: list[Insight]) -> None:
    if m.volatility > HIGH_VOL:
        out.append(
            Insight(
                severity="warning",
                title="Ton épargne peut bouger fort",
                detail=(
                    "Sur une mauvaise année, une baisse de 30 à 40 % est possible. "
                    "Piste : vérifier que ton curseur prudent ↔ dynamique correspond bien "
                    "à ce que tu peux supporter."
                ),
            )
        )


_RULES = (_concentration, _correlation, _sharpe, _volatility)
