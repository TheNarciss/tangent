"""Finverse — bank data for the Asian banks neither Powens nor Enable Banking cover.

Finverse aggregates Singapore, Hong Kong, Malaysia and Korea (DBS, POSB,
OCBC…). The person links a bank in Finverse Link; we exchange the code for
a login identity token and its refresh token, and read accounts and
transactions with it. A test application only links Finverse's testbank.

Modules:
- client     : HTTP client (customer token, link token, login identity data)
- aggregator : maps Finverse payloads to the neutral DTOs, syncs a row

Cf ADR-037.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FinverseSettings(BaseSettings):
    """Secrets and URLs, from backend/.env (written there by the deploy, ADR-037)."""

    client_id: str = Field(default="", validation_alias="FINVERSE_CLIENT_ID")
    client_secret: str = Field(default="", validation_alias="FINVERSE_CLIENT_SECRET")
    base_url: str = Field(
        default="https://api.prod.finverse.net", validation_alias="FINVERSE_BASE_URL"
    )
    frontend_url: str = Field(default="http://localhost:5173", validation_alias="FRONTEND_URL")
    backend_url: str = Field(default="http://localhost:8000", validation_alias="BACKEND_URL")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def redirect_uri(self) -> str:
        """Registered as is in Finverse's dashboard: it must not move."""
        return f"{self.backend_url}/auth/finverse/callback"


settings = FinverseSettings()
