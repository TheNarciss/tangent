"""Endpoints pour l'acceptation des CGU/Privacy par l'utilisateur.

Pattern « click-through agreement » : tant qu'un user n'a pas accepté la
version actuelle (cf CURRENT_TERMS_VERSION), le frontend lui affiche
TermsGate qui bloque l'accès au dashboard. Robuste pour bump de version
ultérieur (toute évolution substantielle des pages /legal/* incrémente
CURRENT_TERMS_VERSION → re-acceptance forcée pour tous).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..auth.audit import log_event
from ..auth.terms_version import CURRENT_TERMS_VERSION
from ..db.engine import get_session

router = APIRouter(tags=["terms"])


class TermsVersionPublic(BaseModel):
    """Endpoint public — le frontend a besoin de la version pour comparer."""

    version: str


class AcceptTermsRequest(BaseModel):
    """Body du POST /users/me/accept-terms.

    On exige que le frontend envoie la version qu'il pense accepter, pour
    éviter les races : si la version a bumpé entre le moment où l'user a
    vu le modal et où il a cliqué, on refuse l'acceptation (l'user verra
    le nouveau modal).
    """

    version: str = Field(min_length=1, max_length=20)


class TermsStatus(BaseModel):
    """Réponse après acceptation — ou GET status."""

    version: str
    accepted_at: datetime


@router.get(
    "/auth/terms-version",
    response_model=TermsVersionPublic,
    summary="Version actuelle des CGU/Privacy (public, no auth)",
)
async def get_terms_version() -> TermsVersionPublic:
    """Renvoie la version actuelle des CGU. Public, pas d'auth requise.

    Le frontend l'utilise pour comparer à user.terms_version_accepted et
    décider d'afficher TermsGate.
    """
    return TermsVersionPublic(version=CURRENT_TERMS_VERSION)


@router.post(
    "/users/me/accept-terms",
    response_model=TermsStatus,
    summary="L'utilisateur accepte la version courante des CGU/Privacy",
)
async def accept_terms(
    body: AcceptTermsRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> TermsStatus:
    """Persiste l'acceptation des CGU pour l'user courant.

    Le client doit envoyer la version qu'il accepte. Si elle ne matche pas
    la version serveur actuelle, on rejette (race condition entre affichage
    du modal et clic).
    """
    if body.version != CURRENT_TERMS_VERSION:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                f"Version incompatible : vous avez accepté {body.version!r}, "
                f"la version actuelle est {CURRENT_TERMS_VERSION!r}. "
                "Rechargez la page et acceptez la nouvelle version."
            ),
        )

    user.terms_version_accepted = CURRENT_TERMS_VERSION
    user.terms_accepted_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(user)

    log_event(
        "TERMS_ACCEPTED",
        user_id=str(user.id),
        version=CURRENT_TERMS_VERSION,
    )

    return TermsStatus(
        version=CURRENT_TERMS_VERSION,
        accepted_at=user.terms_accepted_at,
    )
