"""Intégration Powens — Open Banking API pour BNP Paribas + autres.

Modules :
- settings : pydantic-settings loadées depuis .env
- client : HTTP client async vers l'API Powens
- sync : pull /accounts /investments → mappe vers Position locales
- state : tracking du dernier sync (data/powens_state.json)
- webhooks : handler des events CONNECTION_SYNCED etc.
"""
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PowensSettings(BaseSettings):
    """Secrets et config Powens chargés depuis backend/.env

    Si .env absent, on lance les défauts non-fonctionnels — les endpoints
    Powens retourneront 503 avec un message explicite.
    """
    domain: str = Field(default="", validation_alias="POWENS_DOMAIN")
    client_id: str = Field(default="", validation_alias="POWENS_CLIENT_ID")
    client_secret: str = Field(default="", validation_alias="POWENS_CLIENT_SECRET")
    user_token: str = Field(default="", validation_alias="POWENS_USER_TOKEN")
    connection_id: int = Field(default=0, validation_alias="POWENS_CONNECTION_ID")
    webhook_secret: str = Field(default="", validation_alias="POWENS_WEBHOOK_SECRET")
    autosync_threshold_hours: int = Field(default=12, validation_alias="POWENS_AUTOSYNC_THRESHOLD_HOURS")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_configured(self) -> bool:
        """True si tous les secrets essentiels sont remplis."""
        return bool(self.domain and self.user_token and self.connection_id)

    @property
    def base_url(self) -> str:
        return f"https://{self.domain}/2.0"


def load_yaml_config() -> dict:
    """Charge backend/config/powens.yaml — mapping markets, règles d'identification."""
    path = Path(__file__).resolve().parent.parent.parent / "config" / "powens.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# Singletons — chargés une fois au démarrage
settings = PowensSettings()
yaml_config = load_yaml_config()