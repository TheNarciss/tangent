"""Tracking du dernier sync Powens — persisté dans data/powens_state.json."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from . import settings

logger = logging.getLogger(__name__)

_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "powens_state.json"


class SyncState(BaseModel):
    """Métadonnées du dernier sync Powens.

    Persisté en JSON dans data/powens_state.json. Lu par le frontend
    via GET /sync/status pour afficher "Dernière sync il y a 2h" etc.
    """

    last_sync: datetime | None = None
    last_webhook: datetime | None = None
    last_error: str | None = None
    connection_id: int | None = None
    accounts_seen: list[int] = []
    positions_count: int = 0
    cash_balance: float = 0.0

    @property
    def age_hours(self) -> float | None:
        if self.last_sync is None:
            return None
        delta = (
            datetime.now(UTC) - self.last_sync.replace(tzinfo=UTC)
            if self.last_sync.tzinfo is None
            else datetime.now(UTC) - self.last_sync
        )
        return delta.total_seconds() / 3600.0


def load() -> SyncState:
    """Charge le state du dernier sync. Retourne un state vide si jamais sync."""
    if not _PATH.exists():
        return SyncState()
    try:
        return SyncState.model_validate_json(_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("powens_state.json malformé : %s — on repart vide", exc)
        return SyncState()


def save(state: SyncState) -> None:
    """Persiste le state. Crée data/ si absent."""
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def is_stale(threshold_hours: int | None = None) -> bool:
    """True si jamais sync OU dernière sync > threshold heures."""
    if threshold_hours is None:
        threshold_hours = settings.autosync_threshold_hours
    state = load()
    if state.last_sync is None:
        return True
    age = state.age_hours
    return age is None or age > threshold_hours


def mark_error(message: str) -> None:
    """Note une erreur sans toucher au last_sync (= la dernière sync réussie reste valide)."""
    state = load()
    state.last_error = f"{datetime.now(UTC).isoformat()} — {message}"
    save(state)


def clear_error() -> None:
    state = load()
    if state.last_error is not None:
        state.last_error = None
        save(state)
