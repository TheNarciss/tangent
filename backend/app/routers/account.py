"""Account management endpoints — user's own account self-service.

Endpoints :
- POST /users/me/change-password   : verify current pwd + set new
- DELETE /users/me                 : delete account + cascade all data
- GET /users/me/oauth-accounts     : list linked OAuth accounts
- DELETE /users/me/oauth-accounts/{provider} : unlink one (requires password)

Bank connection management (delete a Powens connection + its bank_accounts)
lives in routers/accounts.py since it's tied to the multi-bank aggregation flow.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi_users.password import PasswordHelper
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..auth.audit import log_event
from ..auth.oauth_models import OAuthAccount
from ..db.engine import get_session
from ..db.models import (
    BankAccount,
    PasswordResetToken,
    PowensCredential,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["account"])

_password_helper = PasswordHelper()


# ── Schemas ───────────────────────────────────────────────────────────


class ChangePasswordRequest(BaseModel):
    """Body for POST /users/me/change-password."""

    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class DeleteAccountRequest(BaseModel):
    """Body for DELETE /users/me.

    Confirmation string MUST equal "DELETE" (case-sensitive). If the user has a
    password, current_password is also required for re-authentication.
    """

    confirmation: str = Field(min_length=1, max_length=20)
    current_password: str | None = Field(default=None, max_length=200)


# ── Change password ───────────────────────────────────────────────────


@router.post(
    "/users/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the current user's password (requires current password)",
)
async def change_password(
    body: ChangePasswordRequest,
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """Verify current password, then update to new password.

    Refuses if the user has no password (e.g. Google-only account) — they
    should set a password via a dedicated flow first (not in this PR).
    """
    if not user.hashed_password:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=("No password set on this account (OAuth-only). Set a password first."),
        )

    valid, _ = _password_helper.verify_and_update(body.current_password, user.hashed_password)
    if not valid:
        log_event(
            "PASSWORD_CHANGE_FAILED",
            user_id=str(user.id),
            reason="wrong_current_password",
        )
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    user.hashed_password = _password_helper.hash(body.new_password)
    await session.commit()
    log_event("PASSWORD_CHANGED", user_id=str(user.id))

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Delete account (GDPR right to erasure) ────────────────────────────


@router.post(
    "/users/me/delete-account",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete current user's account + all associated data (irreversible)",
)
async def delete_my_account(
    body: DeleteAccountRequest,
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """Permanently delete the current user's account and all related data.

    Confirmation flow:
    - body.confirmation MUST equal exactly "DELETE" (typed by the user)
    - If the user has a password, body.current_password is required (re-auth)
    - If OAuth-only, no password re-auth needed (cookie already proves identity)

    Cascade: explicitly deletes data in tables that may not have ON DELETE
    CASCADE configured at the FK level, then deletes the user row itself.
    """
    if body.confirmation != "DELETE":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail='Confirmation must be exactly "DELETE".',
        )

    # Re-auth via password if the user has one
    if user.hashed_password:
        if not body.current_password:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="current_password is required.",
            )
        valid, _ = _password_helper.verify_and_update(body.current_password, user.hashed_password)
        if not valid:
            log_event(
                "ACCOUNT_DELETE_FAILED",
                user_id=str(user.id),
                reason="wrong_password",
            )
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )

    user_id = user.id
    user_email = user.email

    # Explicit cascade — robust to whatever the FK ON DELETE config is.
    # Child tables FIRST (in dependency order), then the user row.
    await session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id))
    await session.execute(delete(PowensCredential).where(PowensCredential.user_id == user_id))
    # BankAccount cascade auto sur Loan/Holdings/Transactions via FK ON DELETE CASCADE
    await session.execute(delete(BankAccount).where(BankAccount.user_id == user_id))

    await session.execute(delete(OAuthAccount).where(OAuthAccount.user_id == user_id))

    # Profile (table user_profile JSON-blob)
    try:
        from ..db.models import Profile

        await session.execute(delete(Profile).where(Profile.user_id == user_id))
    except ImportError:
        pass

    # Watchlist
    try:
        from ..db.models import WatchlistItem

        await session.execute(delete(WatchlistItem).where(WatchlistItem.user_id == user_id))
    except ImportError:
        pass

    # Portfolios (cascade auto sur positions via FK)
    try:
        from ..db.models import Portfolio

        await session.execute(delete(Portfolio).where(Portfolio.user_id == user_id))
    except ImportError:
        pass

    # Finally the user
    await session.delete(user)
    await session.commit()

    log_event("ACCOUNT_DELETED", user_id=str(user_id), email=user_email)
    logger.info("Account deleted: user_id=%s", user_id)

    # Clear auth cookie via Response (frontend will get 204 + cleared cookie)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(key="tangent_auth", httponly=True, samesite="lax", secure=True)
    return response
