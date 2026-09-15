"""The morning briefing runs the LLM every night: only an administrator may opt in."""

from __future__ import annotations

import secrets

import pytest
from sqlalchemy import select, update

from app.auth.models import User
from app.db.engine import async_session_factory
from app.repositories import profile as profile_repo


async def _login(client, *, superuser: bool) -> str:
    email = f"brief-{'admin' if superuser else 'user'}-{secrets.token_hex(4)}@test.com"
    pwd = "TestPwd123!"
    client.cookies.clear()
    await client.post("/api/auth/register", json={"email": email, "password": pwd})
    if superuser:
        async with async_session_factory() as session:
            await session.execute(update(User).where(User.email == email).values(is_superuser=True))
            await session.commit()
    await client.post("/api/auth/login", data={"username": email, "password": pwd})
    return email


@pytest.mark.integration
async def test_only_an_admin_can_switch_the_briefing_on(client):
    await _login(client, superuser=False)
    resp = await client.put("/api/profile", json={"auto_review_enabled": True})
    assert resp.status_code == 403
    assert "administrateurs" in resp.json()["detail"]

    # The rest of the profile stays editable.
    resp = await client.put("/api/profile", json={"horizon_years": 12})
    assert resp.status_code == 200
    assert resp.json()["auto_review_enabled"] is False

    admin = await _login(client, superuser=True)
    resp = await client.put("/api/profile", json={"auto_review_enabled": True})
    assert resp.status_code == 200
    assert resp.json()["auto_review_enabled"] is True

    async with async_session_factory() as session:
        admin_id = (await session.execute(select(User.id).where(User.email == admin))).scalar()
        opted = await profile_repo.list_opted_in_users(session)
    assert admin_id in {p.user_id for p in opted}


@pytest.mark.integration
async def test_a_flag_set_before_the_rule_does_not_put_a_user_in_the_night_batch(client):
    email = await _login(client, superuser=False)
    async with async_session_factory() as session:
        user_id = (await session.execute(select(User.id).where(User.email == email))).scalar()
        await profile_repo.update(session, user_id, {"auto_review_enabled": True})
        opted = await profile_repo.list_opted_in_users(session)
    assert user_id not in {p.user_id for p in opted}
