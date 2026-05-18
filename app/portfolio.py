"""Portfolio persistence. Single JSON file, no DB needed at this scale."""
import logging
from pathlib import Path

from pydantic import ValidationError

from .errors import PortfolioCorruptedError
from .models import Portfolio

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent / "data" / "portfolio.json"


def load() -> Portfolio:
    if not _PATH.exists():
        logger.warning("portfolio.json missing; returning empty portfolio")
        return Portfolio(positions=[])
    try:
        return Portfolio.model_validate_json(_PATH.read_text())
    except ValidationError as exc:
        raise PortfolioCorruptedError(
            f"portfolio.json malformé: {exc.error_count()} erreur(s) de validation."
        ) from exc
    except OSError as exc:
        raise PortfolioCorruptedError(f"Impossible de lire portfolio.json: {exc}") from exc


def save(portfolio: Portfolio) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        _PATH.write_text(portfolio.model_dump_json(indent=2))
    except OSError as exc:
        raise PortfolioCorruptedError(f"Impossible d'écrire portfolio.json: {exc}") from exc