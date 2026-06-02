"""Chiffrement Fernet des tokens OAuth au repos (cf ADR-014 §5, ADR-012).

Clé dédiée OAUTH_TOKEN_ENCRYPTION_KEY — séparée de POWENS_TOKEN_ENCRYPTION_KEY
pour réduire le blast radius en cas de compromission. Procédure de rotation
identique à ADR-012 (Fernet 32 bytes base64url, backup Bitwarden obligatoire,
perte = re-OAuth forcé pour tous les users).

Expose :
- encrypt_token / decrypt_token : helpers bas niveau
- EncryptedToken : TypeDecorator SQLAlchemy à utiliser dans le modèle
  OAuthAccount à la place de String — chiffrement transparent côté ORM.

Lazy init : le Fernet n'est construit qu'au premier appel, pour ne pas
crasher l'import du modèle quand la clé est absente (dev sans OAuth, etc.).
"""

from __future__ import annotations

import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import LargeBinary
from sqlalchemy.types import TypeDecorator

_KEY_ENV = "OAUTH_TOKEN_ENCRYPTION_KEY"
_PLACEHOLDER = "GENERATE_ME_WITH_FERNET_GENERATE_KEY"

_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    """Lazy-init du Fernet — crash explicite si la clé n'est pas configurée."""
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance
    key = os.getenv(_KEY_ENV, "")
    if not key or key == _PLACEHOLDER:
        raise RuntimeError(
            f"{_KEY_ENV} manquant ou laissé au placeholder. "
            'Génère-en un fort : python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())" '
            "puis mets-le dans backend/.env. Sauvegarde-le aussi en password "
            "manager — perte = re-OAuth forcé pour tous les users (cf ADR-012)."
        )
    _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet_instance


def encrypt_token(plaintext: str | None) -> bytes | None:
    """Chiffre un token. None passe-through (champ optionnel)."""
    if plaintext is None:
        return None
    return _get_fernet().encrypt(plaintext.encode())


def decrypt_token(ciphertext: bytes | None) -> str | None:
    """Déchiffre un token. None passe-through. Lève RuntimeError si tampered."""
    if ciphertext is None:
        return None
    try:
        return _get_fernet().decrypt(ciphertext).decode()
    except InvalidToken as exc:
        raise RuntimeError(
            f"Token OAuth corrompu ou clé Fernet invalide — vérifier {_KEY_ENV}"
        ) from exc


class EncryptedToken(TypeDecorator[str]):
    """SQLAlchemy TypeDecorator chiffrant les tokens OAuth au repos.

    Stocké en BYTEA, manipulé comme str côté Python. Transparent pour l'ORM :
    on lit/écrit des str, le chiffrement est invisible.
    """

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Any) -> bytes | None:
        return encrypt_token(value)

    def process_result_value(self, value: bytes | None, dialect: Any) -> str | None:
        return decrypt_token(value)
