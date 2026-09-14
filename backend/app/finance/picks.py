"""« La liste de l'année », computed on a schedule and served from a file.

The list moves once a quarter and the same list serves every user, so no
request should ever pay for it: the scheduler recomputes it once a day (and
shortly after a restart when the stored copy is stale) and writes it to
`data/picks.json`. The route reads the file. A first boot has nothing to
serve for a few minutes, and says so.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..errors import AppError
from ..models import PicksResponse, PicksTrackRecord, PicksYearRow
from . import momentum

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "picks.json"
FRESH_FOR = timedelta(hours=24)

# The last list computed by this process: what the route serves when the
# data directory cannot be written (a bind mount owned by another user).
_MEMORY: PicksResponse | None = None


def build() -> PicksResponse:
    """The list, what changed since the last review, and the rule's track record."""
    cfg = momentum.config()
    tickers = momentum.universe(cfg)
    daily = momentum.prices(tickers)
    bt = momentum.backtest(daily, cfg)
    picks = momentum.current(daily, cfg)
    return PicksResponse(
        computed_at=datetime.now(UTC).isoformat(timespec="seconds"),
        as_of=str(picks.as_of.date()),
        next_review=str(picks.next_review.date()),
        review=cfg.review,
        guard_on=picks.guard_on,
        held=picks.held,
        bought=picks.bought,
        sold=picks.sold,
        universe_size=len(daily.columns),
        indices=cfg.universe,
        top=cfg.top,
        track_record=PicksTrackRecord(
            since=str(bt.strategy.index[0].date()),
            cagr=bt.cagr,
            universe_cagr=bt.universe_cagr,
            max_drawdown=bt.max_drawdown,
            universe_max_drawdown=bt.universe_max_drawdown,
            turnover=bt.turnover,
            reviews=len(bt.reviews),
            guarded_reviews=sum(1 for r in bt.reviews if r.guard_on),
            yearly=[
                PicksYearRow(
                    year=int(year), strategy=float(row["strategy"]), universe=float(row["universe"])
                )
                for year, row in bt.yearly.iterrows()
            ],
        ),
    )


def refresh() -> PicksResponse:
    """Recompute the list and store it. Raises AppError when a source is out of reach.

    A data directory that cannot be written costs a warning, not the list:
    the process keeps it in memory until the next restart.
    """
    global _MEMORY
    out = build()
    _MEMORY = out
    try:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        _PATH.write_text(out.model_dump_json())
        logger.info("picks: liste recalculée, %d titres, écrite dans %s", len(out.held), _PATH)
    except OSError as exc:
        logger.error(
            "picks: liste recalculée (%d titres) mais %s n'est pas inscriptible (%s) : "
            "servie depuis la mémoire jusqu'au prochain redémarrage",
            len(out.held),
            _PATH,
            exc,
        )
    return out


def load() -> PicksResponse | None:
    """The stored list, or None when nothing has been computed yet."""
    if not _PATH.exists():
        return _MEMORY
    try:
        return PicksResponse.model_validate_json(_PATH.read_text())
    except (OSError, ValueError):
        logger.warning("picks: fichier illisible, il sera recalculé: %s", _PATH)
        return _MEMORY


def is_fresh() -> bool:
    """Whether the stored list is recent enough to skip the boot-time recompute."""
    stored = load()
    if stored is None:
        return False
    computed = datetime.fromisoformat(stored.computed_at)
    return datetime.now(UTC) - computed < FRESH_FOR


def refresh_if_stale() -> None:
    """What the scheduler runs: recompute unless the stored copy is fresh."""
    if is_fresh():
        logger.info("picks: liste du jour déjà en place")
        return
    try:
        refresh()
    except AppError as exc:
        logger.warning("picks: sources injoignables, liste non recalculée: %s", exc)
