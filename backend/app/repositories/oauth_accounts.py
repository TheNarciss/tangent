"""Repository pour OAuthAccount — couche d'accès DB pure (cf ADR-009).

Toutes les fonctions filtrent par user_id (cf ADR-002 §4 multi-tenancy).
Ne logge pas, ne valide pas, ne commit pas — c'est au router de gérer.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.oauth_models import OAuthAccount


async def list_oauth_accounts_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[OAuthAccount]:
    """Liste les comptes OAuth d'un user. Filtré par user_id (ADR-002)."""
    result = await session.execute(select(OAuthAccount).where(OAuthAccount.user_id == user_id))
    return list(result.scalars().all())


async def get_oauth_account_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> OAuthAccount | None:
    """Récupère un compte OAuth par id, ssi il appartient au user_id.

    Le double filtre (id + user_id) est volontaire : c'est le verrou
    multi-tenant. Un user qui tape l'UUID d'un account d'un autre user
    reçoit None (équivalent 404), pas le account de l'autre.
    """
    # mypy infère bool au lieu de ColumnElement[bool] pour OAuthAccount.id
    # à cause du mixin fastapi-users-db-sqlalchemy (sans plugin SA pour mypy).
    # Runtime: == retourne bien ColumnElement[bool], le filtre fonctionne.
    result = await session.execute(
        select(OAuthAccount).where(
            OAuthAccount.id == account_id,  # type: ignore[arg-type]
            OAuthAccount.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_oauth_account_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
) -> OAuthAccount | None:
    """Supprime un compte OAuth s'il appartient au user. Retourne l'objet
    supprimé (utile pour logging au router) ou None si non trouvé.

    Le caller doit faire session.commit().
    """
    target = await get_oauth_account_for_user(session, user_id, account_id)
    if target is None:
        return None
    await session.delete(target)
    return target
