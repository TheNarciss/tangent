"""Audit log — trace les actions sensibles pour analyse forensique.

Pattern : logs structurés (clés=valeurs) → faciles à grep / parser.
Stockés dans le même handler que le logger principal (sortie stdout en dev,
fichier rotaté en prod).

Événements tracés :
- AUTH_REGISTER : nouveau compte créé
- AUTH_LOGIN_SUCCESS : connexion réussie
- AUTH_LOGIN_FAIL : tentative de login échouée (mauvais password ou user inconnu)
- AUTH_LOGOUT : déconnexion
- AUTH_PASSWORD_RESET_REQUEST : demande de reset
- AUTH_PASSWORD_RESET_CONFIRM : reset effectif
- RATE_LIMIT_HIT : tentative bloquée par rate limit
- (Phase 5) POWENS_TOKEN_CREATED, POWENS_TOKEN_REVOKED, POWENS_SYNC_TRIGGERED
"""
import logging
from datetime import datetime, timezone

# Logger dédié — plus simple à filtrer/router que le logger app racine
_audit = logging.getLogger("audit")


def log_event(event: str, **fields) -> None:
    """Log un événement audit avec un format consistent : clé=val pour grep.

    Exemple :
        log_event("AUTH_LOGIN_SUCCESS", user_id="abc-123", ip="1.2.3.4")

    Sortie :
        2026-05-21T12:34:56Z AUDIT AUTH_LOGIN_SUCCESS user_id=abc-123 ip=1.2.3.4
    """
    ts = datetime.now(timezone.utc).isoformat()
    parts = [f"{k}={v}" for k, v in fields.items() if v is not None]
    _audit.info("AUDIT %s ts=%s %s", event, ts, " ".join(parts))