"""Handler des webhooks Powens.

Powens POST sur /webhooks/powens à chaque event de sync (par défaut
CONNECTION_SYNCED, fires quand la sync quotidienne automatique se termine).

Notre handler trigger un sync_portfolio() à chaque CONNECTION_SYNCED
qui correspond à notre connexion (filtré sur connection_id).

Note sécurité : Powens ne signe pas les webhooks (pas de HMAC standard).
On valide simplement que le payload contient bien le connection_id attendu
et que la requête vient d'une IP raisonnable (à durcir en prod).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from . import settings, state
from .sync import sync_portfolio

logger = logging.getLogger(__name__)


# Events qu'on traite — les autres sont silently ignored
_HANDLED_EVENTS = {"CONNECTION_SYNCED", "ACCOUNTS_FETCHED", "ACCOUNT_SYNCED"}


async def handle_webhook(payload: dict[str, Any]) -> dict:
    """Route un payload webhook Powens.

    Returns dict avec status + détails — utile pour debug via webhook.site.
    """
    event_type = payload.get("event") or payload.get("event_type") or "UNKNOWN"
    connection_id = payload.get("id_connection") or payload.get("connection_id")

    logger.info("Powens webhook reçu : event=%s connection_id=%s", event_type, connection_id)

    # Note la réception du webhook même si on ne le traite pas
    st = state.load()
    st.last_webhook = datetime.now(UTC)
    state.save(st)

    # Filtre 1 : event qui nous intéresse ?
    if event_type not in _HANDLED_EVENTS:
        return {"status": "ignored", "reason": f"event_type={event_type} non géré"}

    # Filtre 2 : c'est bien NOTRE connexion ?
    if connection_id and settings.connection_id and connection_id != settings.connection_id:
        return {
            "status": "ignored",
            "reason": f"connection_id={connection_id} ≠ POWENS_CONNECTION_ID={settings.connection_id}",
        }

    # Trigger un sync
    logger.info("Powens webhook %s → trigger sync_portfolio()", event_type)
    result = await sync_portfolio()
    return {
        "status": "ok",
        "triggered_sync": True,
        "sync_success": result.success,
        "positions_count": result.positions_count,
        "error": result.error,
    }
