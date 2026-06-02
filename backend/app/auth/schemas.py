"""Schemas Pydantic pour les users — input/output API.

IMPORTANT : ces schemas définissent ce qui transite via l'API. Le
hashed_password n'est JAMAIS dans UserRead (output) — il reste interne.
"""

import uuid
from datetime import datetime

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Ce que le frontend reçoit. Ne contient PAS hashed_password."""

    display_name: str | None = None
    terms_version_accepted: str | None = None
    terms_accepted_at: datetime | None = None
    has_password: bool = True  # computed property (cf User model)


class UserCreate(schemas.BaseUserCreate):
    """Ce que le frontend envoie pour POST /auth/register."""

    display_name: str | None = None


class UserUpdate(schemas.BaseUserUpdate):
    """Ce que le frontend envoie pour PATCH /users/me."""

    display_name: str | None = None
