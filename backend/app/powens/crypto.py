import logging
from cryptography.fernet import Fernet
from . import settings

logger = logging.getLogger(__name__)

_fernet = None
if settings.token_encryption_key:
    try:
        _fernet = Fernet(settings.token_encryption_key.encode())
    except ValueError as e:
        logger.error(f"Invalid encryption key for Powens: {e}")

def encrypt_token(token: str) -> str:
    if not _fernet:
        # Fallback if unconfigured? Or error out? Better to error out.
        raise ValueError("POWENS_TOKEN_ENCRYPTION_KEY is not configured or invalid.")
    return _fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    if not _fernet:
        raise ValueError("POWENS_TOKEN_ENCRYPTION_KEY is not configured or invalid.")
    return _fernet.decrypt(encrypted_token.encode()).decode()
