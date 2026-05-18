"""Portfolio persistence. Single JSON file, no DB needed at this scale."""
import logging
from pathlib import Path

from pydantic import ValidationError

from . import transactions, watchlist
from .errors import PortfolioCorruptedError
from .models import Portfolio, Position

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent / "data" / "portfolio.json"


def load() -> Portfolio:
    """Charge le portfolio puis merge la watchlist comme positions à quantity=0.

    Les tickers de la watchlist n'ont pas de transaction réelle → apparaissent
    dans le dashboard et sont considérés par l'optimiseur sans modifier la valo.
    """
    if transactions.exists():
        pf = transactions.derive_portfolio(transactions.load())
    elif _PATH.exists():
        try:
            pf = Portfolio.model_validate_json(_PATH.read_text())
        except ValidationError as exc:
            raise PortfolioCorruptedError(
                f"portfolio.json malformé: {exc.error_count()} erreur(s) de validation."
            ) from exc
        except OSError as exc:
            raise PortfolioCorruptedError(f"Impossible de lire portfolio.json: {exc}") from exc
    else:
        logger.warning("portfolio.json missing; returning empty portfolio")
        pf = Portfolio(positions=[])

    # Merge watchlist : tickers suivis mais sans transaction
    held = {p.ticker for p in pf.positions}
    watched = watchlist.load()
    for ticker in watched:
        if ticker not in held:
            pf.positions.append(Position(ticker=ticker, quantity=0, avg_cost=0))
    if watched:
        logger.info("portfolio: merged %d watchlist tickers", len(watched))
    return pf


def save(portfolio: Portfolio) -> None:
    if transactions.exists():
        logger.warning("transactions.json present — direct edits to portfolio.json will be ignored on next load")
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        _PATH.write_text(portfolio.model_dump_json(indent=2))
    except OSError as exc:
        raise PortfolioCorruptedError(f"Impossible d'écrire portfolio.json: {exc}") from exc