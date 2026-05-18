"""Portfolio persistence. Single JSON file, no DB needed at this scale."""
from pathlib import Path

from .models import Portfolio

_PATH = Path(__file__).resolve().parent.parent / "data" / "portfolio.json"


def load() -> Portfolio:
    if not _PATH.exists():
        return Portfolio(positions=[])
    return Portfolio.model_validate_json(_PATH.read_text())


def save(portfolio: Portfolio) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(portfolio.model_dump_json(indent=2))
