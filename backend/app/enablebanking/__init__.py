"""Enable Banking — PSD2 account information for the banks Powens does not cover.

Enable Banking holds the licence and the eIDAS certificate; we hold an RSA
key that signs the JWT authorising our calls. The production application
runs in restricted mode: only the accounts the owner linked in Enable
Banking's control panel are readable. Revolut is the first bank behind it.

Modules:
- client     : HTTP client (JWT RS256, /auth, /sessions, /accounts)
- aggregator : maps Enable Banking payloads to the neutral DTOs, syncs a row

Cf ADR-032.
"""

from __future__ import annotations

import base64
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnableBankingSettings(BaseSettings):
    """Secrets and URLs, from backend/.env."""

    app_id: str = Field(default="", validation_alias="ENABLEBANKING_APP_ID")
    private_key_b64: str = Field(default="", validation_alias="ENABLEBANKING_PRIVATE_KEY_B64")
    base_url: str = Field(
        default="https://api.enablebanking.com", validation_alias="ENABLEBANKING_BASE_URL"
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
        return bool(self.app_id and self.private_key_b64)

    @property
    def private_key_pem(self) -> str:
        return base64.b64decode(self.private_key_b64).decode()

    @property
    def redirect_url(self) -> str:
        return f"{self.backend_url}/auth/enablebanking/callback"


settings = EnableBankingSettings()
