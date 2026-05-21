"""Watchlist : tickers à surveiller sans transaction réelle.

Stockés dans data/watchlist.json (simple list[str]). Mergés au portfolio dérivé
des transactions avec quantity=0 → apparaissent dans le dashboard et sont
considérés par l'optimiseur sans impacter la valorisation actuelle.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent / "data" / "watchlist.json"


def load() -> list[str]:
    """Liste des tickers suivis, jamais d'erreur (retourne [] si problème)."""
    if not _PATH.exists():
        return []
    try:
        raw = json.loads(_PATH.read_text())
        if isinstance(raw, list):
            return [str(t).strip().upper() for t in raw if t]
        return []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("watchlist.json malformé: %s", exc)
        return []


def add(ticker: str) -> list[str]:
    """Ajoute un ticker (dédupliqué, normalisé majuscules). Retourne la liste finale."""
    t = ticker.strip().upper()
    if not t:
        return load()
    tickers = load()
    if t not in tickers:
        tickers.append(t)
        _save(tickers)
        logger.info("watchlist: added %s", t)
    return tickers


def remove(ticker: str) -> list[str]:
    """Retire un ticker. Retourne la liste finale."""
    t = ticker.strip().upper()
    tickers = [x for x in load() if x != t]
    _save(tickers)
    logger.info("watchlist: removed %s", t)
    return tickers


def _save(tickers: list[str]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(tickers, indent=2))