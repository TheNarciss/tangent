"""The linked-accounts list names every provider the app signs in with.

Regression: an account created with Sign in with Apple made
GET /users/me/oauth-accounts answer 500 (the public view only knew Google),
which is what Apple's reviewer hit on 2026-09-22.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.routers.oauth_accounts import OAuthAccountPublic


@pytest.mark.parametrize("provider", ["google", "apple"])
def test_every_sign_in_provider_has_a_public_view(provider: str):
    view = OAuthAccountPublic(
        id=uuid.uuid4(), oauth_name=provider, account_email="x@privaterelay.appleid.com"
    )
    assert view.oauth_name == provider


def test_an_unknown_provider_is_still_refused():
    with pytest.raises(ValidationError):
        OAuthAccountPublic(id=uuid.uuid4(), oauth_name="facebook", account_email="x@y.z")
