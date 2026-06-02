"""Module auth — login, register, JWT, OAuth, multi-tenant deps.

Exports :
- fastapi_users : instance singleton
- current_user / current_active_user / current_superuser : FastAPI dependencies
- auth_backend : cookie+JWT backend
- User, UserCreate, UserRead, UserUpdate : modèles/schemas
- OAuthAccount : modèle des comptes OAuth liés (ADR-014)
"""

import uuid

from fastapi_users import FastAPIUsers

from .backend import auth_backend
from .manager import get_user_manager
from .models import Base, User
from .oauth_models import OAuthAccount
from .schemas import UserCreate, UserRead, UserUpdate

# Singleton FastAPIUsers — utilisé par les routes et les deps
# User.hashed_password nullable (ADR-014) — runtime safe, mais viole UserProtocol
fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])  # type: ignore[type-var]

# Dependencies prêtes à l'emploi pour les endpoints
current_user = fastapi_users.current_user()
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)


__all__ = [
    "Base",
    "OAuthAccount",
    "User",
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "auth_backend",
    "current_active_user",
    "current_superuser",
    "current_user",
    "fastapi_users",
]
