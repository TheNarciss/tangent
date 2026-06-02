"""Endpoints pour gérer les comptes OAuth liés d'un user (cf ADR-014).

GET /users/me/oauth-accounts : liste les providers liés (sans tokens)
DELETE /users/me/oauth-accounts/{id} : délie un provider

Note (ADR-009) : l'accès DB passe par app/repositories/oauth_accounts.py.
"""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..auth.audit import log_event
from ..db import get_session
from ..repositories.oauth_accounts import (
    delete_oauth_account_for_user,
    list_oauth_accounts_for_user,
)

router = APIRouter(prefix="/users/me/oauth-accounts", tags=["auth"])


class OAuthAccountPublic(BaseModel):
    """Vue publique d'un compte OAuth lié — JAMAIS les tokens."""

    id: uuid.UUID
    oauth_name: Literal["google"]
    account_email: str


@router.get("", response_model=list[OAuthAccountPublic])
async def list_my_oauth_accounts(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[OAuthAccountPublic]:
    """Liste les providers OAuth liés au user courant. Tokens jamais exposés."""
    accounts = await list_oauth_accounts_for_user(session, user.id)
    return [
        OAuthAccountPublic(
            id=acc.id,
            oauth_name=acc.oauth_name,
            account_email=acc.account_email,
        )
        for acc in accounts
    ]


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_my_oauth_account(
    account_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Délie un compte OAuth.

    Refuse si c'est le seul moyen d'auth (pas de password ET un seul OAuth),
    pour ne pas laisser l'user sans moyen de se reconnecter.
    """
    # Garde-fou avant delete : si pas de password + 1 seul OAuth → blocage
    has_password = user.hashed_password is not None
    accounts_count = len(user.oauth_accounts)
    if not has_password and accounts_count <= 1:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                "Impossible de délier ce compte : c'est ton seul moyen de connexion. "
                "Définis d'abord un mot de passe."
            ),
        )

    deleted = await delete_oauth_account_for_user(session, user.id, account_id)
    if deleted is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="OAuth account not found")
    await session.commit()

    log_event(
        "OAUTH_ACCOUNT_DELETED",
        user_id=str(user.id),
        oauth_name=deleted.oauth_name,
    )
