"""Admin routes — restricted to superusers."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, fastapi_users
from ..db import get_session

router = APIRouter(prefix="/admin", tags=["admin"])

_superuser = fastapi_users.current_user(active=True, superuser=True)


@router.get("/users")
async def list_users(
    superuser: User = Depends(_superuser),
    session: AsyncSession = Depends(get_session),
):
    """List all user accounts. Reserved for superusers.

    Important: returns id + email + flags but NEVER the hashed_password.
    """
    result = await session.execute(select(User))
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
            "is_active": u.is_active,
            "is_superuser": u.is_superuser,
            "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]
