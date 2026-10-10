"""A connection in error is repaired in place, not added again beside itself."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException

from app.powens.client import PowensError
from app.routers import powens as powens_routes


@pytest.fixture
def configured(monkeypatch):
    settings = powens_routes.powens_settings
    monkeypatch.setattr(settings, "domain", "tangent-sandbox.biapi.pro")
    monkeypatch.setattr(settings, "client_id", "client-123")
    monkeypatch.setattr(settings, "backend_url", "https://riskybusinesses.uk")
    monkeypatch.setattr(powens_routes, "decrypt_token", lambda _: "user-token")


class _Session:
    def __init__(self, credential):
        self._credential = credential

    async def execute(self, _stmt):
        found = self._credential
        return SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: found))


def _client(code: str | None):
    class Client:
        def __init__(self, token: str):
            assert token == "user-token"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get_temporary_code(self) -> str:
            if code is None:
                raise PowensError("down")
            return code

    return Client


async def _call(session, platform="web"):
    user = SimpleNamespace(id=uuid.uuid4())
    out = await powens_routes.get_powens_reconnect_webview(
        connection_id=42, platform=platform, user=user, session=session
    )
    return user, out["webview_url"]


async def test_the_webview_reopens_that_very_connection(configured, monkeypatch):
    monkeypatch.setattr(powens_routes, "PowensClient", _client("tmp-code"))
    user, url = await _call(_Session(SimpleNamespace(encrypted_token="x")), platform="app")

    parts = urlparse(url)
    assert (parts.scheme, parts.netloc, parts.path) == ("https", "webview.powens.com", "/reconnect")
    query = {k: v[0] for k, v in parse_qs(parts.query).items()}
    assert query["connection_id"] == "42"
    assert query["code"] == "tmp-code"
    assert query["domain"] == "tangent-sandbox.biapi.pro"
    assert query["client_id"] == "client-123"
    assert query["redirect_uri"] == "https://riskybusinesses.uk/auth/powens/callback"
    claims = powens_routes._read_state(query["state"])
    assert (claims["sub"], claims["platform"]) == (str(user.id), "app")


async def test_without_a_powens_link_there_is_nothing_to_reconnect(configured):
    with pytest.raises(HTTPException) as err:
        await _call(_Session(None))
    assert err.value.status_code == 404


async def test_powens_down_is_said_not_hidden(configured, monkeypatch):
    monkeypatch.setattr(powens_routes, "PowensClient", _client(None))
    with pytest.raises(HTTPException) as err:
        await _call(_Session(SimpleNamespace(encrypted_token="x")))
    assert err.value.status_code == 502
