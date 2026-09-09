"""Rule-based diagnostic on portfolio metrics, written for a non-expert.

Each insight is one plain sentence about what is going on and, when useful,
one "Piste :" (a hint) the reader can act on. No Greek letters, no ratios.

Each rule is a small function `_<rule_name>(metrics, context, out)` that may
append to `out`. To add a new rule, write a function and register it in
`_RULES`. Thresholds live in `config/diagnostic.yaml`.

The rules read what an instrument *is* — a fund or a share, on which index —
rather than inferring it from statistics. Two trackers of the same index are
not "correlated at 0.91", they are the same bet; a single world ETF at 100 %
is the textbook recommendation, not a concentration alert.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ..errors import ConfigurationError
from ..models import AssetMetrics, Insight, PortfolioMetrics

logger = logging.getLogger(__name__)
_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "diagnostic.yaml"

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "good": 2}


class ConcentrationThresholds(BaseModel):
    single_line_max: float = Field(gt=0, le=1)


class SharpeThresholds(BaseModel):
    reference: float
    margin: float = Field(ge=0)


class VolatilityThresholds(BaseModel):
    alert_min: float = Field(gt=0)
    bad_year_sigmas: float = Field(gt=0)


class DiagnosticConfig(BaseModel):
    max_insights: int = Field(gt=0)
    concentration: ConcentrationThresholds
    sharpe: SharpeThresholds
    volatility: VolatilityThresholds


@dataclass(frozen=True)
class Context:
    """What the rules need beyond the metrics themselves.

    `worst_year` is the worst twelve months actually observed for the
    portfolio's dominant asset class. `None` when no long history covers it —
    the volatility rule then says so instead of pretending.
    """

    worst_year: float | None = None
    worst_year_label: str | None = None


@lru_cache(maxsize=1)
def config() -> DiagnosticConfig:
    if not _PATH.exists():
        raise ConfigurationError("diagnostic.yaml introuvable.")
    try:
        raw = yaml.safe_load(_PATH.read_text()) or {}
        return DiagnosticConfig.model_validate(raw)
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError(f"diagnostic.yaml malformé: {exc}") from exc


def generate(m: PortfolioMetrics, context: Context | None = None) -> list[Insight]:
    """Insights for one portfolio, most serious first, capped by `max_insights`."""
    ctx = context or Context()
    insights: list[Insight] = []
    for rule in _RULES:
        rule(m, ctx, insights)

    insights.sort(key=lambda i: _SEVERITY_ORDER.get(i.severity, 9))
    return insights[: config().max_insights]


def _pct(x: float) -> str:
    """French percent: 60 % (space before the sign)."""
    return f"{x * 100:.0f} %"


def _name(a: AssetMetrics) -> str:
    return a.label or a.ticker


def _join(names: list[str]) -> str:
    """'A, B et C' — the French way, so the sentence works with two funds or five."""
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} et {names[-1]}"


def _duplicates(m: PortfolioMetrics, ctx: Context, out: list[Insight]) -> None:
    """Several lines on the same index: one insight for the group, not one per pair."""
    groups: dict[str, list[AssetMetrics]] = {}
    for a in m.assets:
        if a.index_label:
            groups.setdefault(a.index_label, []).append(a)

    for index_label, assets in groups.items():
        if len(assets) < 2:
            continue
        names = _join([_name(a) for a in assets])
        weight = sum(a.weight for a in assets)
        out.append(
            Insight(
                severity="warning",
                title=f"{len(assets)} de tes fonds suivent le même indice",
                detail=(
                    f"{names} suivent tous « {index_label} » : ils montent et baissent "
                    f"ensemble, et pèsent {_pct(weight)} de tes placements. En garder "
                    f"plusieurs ne te protège pas plus qu'un seul. "
                    f"Piste : concentrer les versements sur celui dont les frais sont les plus bas."
                ),
            )
        )


def _concentration(m: PortfolioMetrics, ctx: Context, out: list[Insight]) -> None:
    """A heavy line only matters when it is not itself diversified."""
    limit = config().concentration.single_line_max
    for a in m.assets:
        if a.weight <= limit or a.is_diversified:
            continue

        if a.kind == "stock":
            reason = "c'est une seule société : si elle trébuche, ton épargne trébuche avec elle"
        elif a.index_label:
            reason = (
                f"« {a.index_label} » ne couvre qu'un segment du marché, pas l'économie mondiale"
            )
        else:
            reason = (
                "on ne sait pas ce qu'il y a dedans, donc on ne sait pas ce qu'il te fait risquer"
            )

        out.append(
            Insight(
                severity="warning",
                title=f"Une seule ligne pèse {_pct(a.weight)} de tes placements",
                detail=(
                    f"{_name(a)} fait à lui seul {_pct(a.weight)} du total et {reason}. "
                    f"Piste : diriger les prochains versements vers un fonds plus large."
                ),
            )
        )


def _reward(m: PortfolioMetrics, ctx: Context, out: list[Insight]) -> None:
    """Compare the reward for risk to a century of market history, not to a made-up bar."""
    cfg = config().sharpe
    gap = m.sharpe - cfg.reference
    if abs(gap) <= cfg.margin:
        return  # inside the error of a five-year estimate: nothing to say

    if gap > 0:
        out.append(
            Insight(
                severity="good",
                title="Tes placements te paient bien le risque pris",
                detail=(
                    "Pour les secousses que tu acceptes, le rendement attendu est "
                    "meilleur que celui des actions sur le dernier siècle. Rien à changer."
                ),
            )
        )
    else:
        out.append(
            Insight(
                severity="warning",
                title="Beaucoup de secousses pour peu de rendement attendu",
                detail=(
                    "Tes placements bougent plus que ce que leur rendement espéré "
                    "justifie, comparé aux actions sur le dernier siècle. "
                    "Piste : regarder la proposition ci-dessous."
                ),
            )
        )


def _bad_year(m: PortfolioMetrics, ctx: Context, out: list[Insight]) -> None:
    """Announce a fall measured on real history when we have it, modelled otherwise."""
    cfg = config().volatility
    if m.volatility <= cfg.alert_min:
        return

    if ctx.worst_year is not None:
        drop = abs(ctx.worst_year)
        source = f"La pire année déjà vue sur {ctx.worst_year_label} a coûté {_pct(drop)}"
    else:
        drop = cfg.bad_year_sigmas * m.volatility
        source = f"Sur une mauvaise année, une baisse de {_pct(drop)} est possible"

    out.append(
        Insight(
            severity="warning",
            title="Ton épargne peut bouger fort",
            detail=(
                f"{source}. Piste : vérifier que ton curseur prudent ↔ dynamique "
                f"correspond bien à ce que tu peux supporter."
            ),
        )
    )


_RULES = (_duplicates, _concentration, _reward, _bad_year)
