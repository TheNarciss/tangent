"""Module auth — login, register, JWT, multi-tenant deps.

Exports :
- fastapi_users : instance singleton
- current_user / current_active_user / current_superuser : FastAPI dependencies
- auth_backend : cookie+JWT backend
- User, UserCreate, UserRead, UserUpdate : modèles/schemas
"""
import uuid

from fastapi_users import FastAPIUsers

from .backend import auth_backend
from .manager import get_user_manager
from .models import Base, User
from .schemas import UserCreate, UserRead, UserUpdate


# Singleton FastAPIUsers — utilisé par les routes et les deps
fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Dependencies prêtes à l'emploi pour les endpoints
current_user = fastapi_users.current_user()                       # connecté (active OU pas)
current_active_user = fastapi_users.current_user(active=True)     # connecté ET is_active=True
current_superuser = fastapi_users.current_user(active=True, superuser=True)


__all__ = [
    "auth_backend",
    "Base",
    "User",
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "fastapi_users",
    "current_user",
    "current_active_user",
    "current_superuser",
]