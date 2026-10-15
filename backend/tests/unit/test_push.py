"""Telling a phone its briefing is ready: the token, the payload, the refusals."""

import time

import httpx
import jwt
import pytest

from app import push


def test_the_provider_token_is_signed_with_the_key_and_names_it():
    token = push.provider_token(now=time.time())
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "ES256"
    assert header["kid"] == push.KEY_ID
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["iss"] == push.TEAM_ID


def test_the_token_is_reused_until_it_ages_then_renewed():
    push._token = None
    now = time.time()
    first = push.provider_token(now=now)
    assert push.provider_token(now=now + 60) == first
    assert push.provider_token(now=now + push.TOKEN_LIFETIME + 1) != first


def test_the_payload_speaks_the_person_s_language():
    fr = push.briefing_payload("fr")["aps"]["alert"]
    en = push.briefing_payload("en")["aps"]["alert"]
    assert fr["title"] == "Ton briefing du matin"
    assert en["title"] == "Your morning briefing"
    # Nothing personal travels: no figure, no name.
    assert "€" not in fr["body"] and "€" not in en["body"]


def test_the_environment_picks_the_host():
    assert push.HOSTS["sandbox"] != push.HOSTS["production"]
    assert push.host().startswith("https://")


@pytest.mark.asyncio
async def test_nothing_to_send_is_not_an_error():
    assert await push.send([], push.briefing_payload("fr")) == []


@pytest.mark.asyncio
async def test_a_retired_token_is_reported_dead_and_the_others_still_go(monkeypatch):
    seen: list[str] = []

    async def fake_post(self, url, **kwargs):  # noqa: ANN001
        token = url.rsplit("/", 1)[-1]
        seen.append(token)
        if token == "dead":
            return httpx.Response(
                410, json={"reason": "Unregistered"}, request=httpx.Request("POST", url)
            )
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    results = await push.send(["alive", "dead"], push.briefing_payload("fr"))
    assert seen == ["alive", "dead"]
    assert [(r.token, r.delivered, r.dead) for r in results] == [
        ("alive", True, False),
        ("dead", False, True),
    ]


@pytest.mark.asyncio
async def test_apns_unreachable_never_raises(monkeypatch):
    async def boom(self, url, **kwargs):  # noqa: ANN001
        raise httpx.ConnectError("nope")

    monkeypatch.setattr(httpx.AsyncClient, "post", boom)
    results = await push.send(["a"], push.briefing_payload("fr"))
    assert [(r.delivered, r.dead, r.reason) for r in results] == [(False, False, "unreachable")]


@pytest.mark.asyncio
async def test_without_a_key_nothing_is_sent_and_nothing_breaks(monkeypatch):
    monkeypatch.setattr(push, "PRIVATE_KEY_B64", "")
    results = await push.send(["a"], push.briefing_payload("fr"))
    assert [(r.delivered, r.reason) for r in results] == [(False, "unconfigured")]
