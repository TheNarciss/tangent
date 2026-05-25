"""Powens webhooks — DISABLED until Phase A.

Powens POST sur /webhooks/powens à chaque event de sync (CONNECTION_SYNCED, etc.).

⚠️ MULTI-TENANT BLOCKER: Le handler ne peut pas mapper id_user Powens →
user_id Tangent sans stocker `powens_user_id` dans powens_credentials.
Désactivé temporairement pour éviter tout sync cross-tenant.

À réactiver en Phase A après l'ajout de la colonne `powens_user_id` et
du mapping correspondant (cf ADR-019).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def handle_webhook(payload: dict[str, Any]) -> dict:
    """[DISABLED — multi-tenant TODO Phase A] Skip all webhook auto-sync.

    Sans mapping id_user Powens → user_id Tangent, on ne peut pas trigger
    un sync user-scoped sans risque de cross-tenant leak.
    """
    event_type = payload.get("event") or payload.get("event_type") or "UNKNOWN"
    connection_id = payload.get("id_connection") or payload.get("connection_id")
    powens_user_id = payload.get("id_user") or payload.get("user_id")

    logger.warning(
        "Powens webhook received but handler disabled — "
        "event=%s connection_id=%s powens_user_id=%s. "
        "Re-enable in Phase A with per-user mapping (cf ADR-019).",
        event_type,
        connection_id,
        powens_user_id,
    )
    return {
        "status": "ignored",
        "reason": "webhook handler disabled (multi-tenant TODO Phase A — cf ADR-019)",
    }
