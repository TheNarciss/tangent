"""Homemade translations for what the server writes to a person (ADR-036).

Two languages, French as the fallback, flat keys per domain, the French and
English of a sentence side by side in ``messages/``. ``t(locale, key, **vars)``
fills ``{name}`` slots with ``str.format``. A request's language comes from
``Accept-Language`` (the frontend sends the language it is showing); a job
that runs with no request (briefing, archive) reads ``profile.locale``.
"""

from __future__ import annotations

from typing import Literal

from fastapi import Request

from .messages import errors, stress, verdicts

Locale = Literal["fr", "en"]
LOCALES: tuple[Locale, ...] = ("fr", "en")
DEFAULT_LOCALE: Locale = "fr"

_FR: dict[str, str] = {**errors.FR, **stress.FR, **verdicts.FR}
_EN: dict[str, str] = {**errors.EN, **stress.EN, **verdicts.EN}
_DICT: dict[Locale, dict[str, str]] = {"fr": _FR, "en": _EN}


def as_locale(value: str | None) -> Locale:
    """A stored or declared value, or French when it is not one of ours."""
    return "en" if value == "en" else "fr"


def negotiate(accept_language: str | None) -> Locale:
    """English if the first language the client lists is English, French otherwise.

    Same rule as the frontend's ``detectLocale``: the first entry decides,
    quality weights are read in the order given (browsers already sort them).
    """
    if not accept_language:
        return DEFAULT_LOCALE
    for part in accept_language.split(","):
        tag = part.split(";")[0].strip().lower()
        if not tag or tag == "*":
            continue
        base = tag.split("-")[0]
        if base == "en":
            return "en"
        if base == "fr":
            return "fr"
    return DEFAULT_LOCALE


def current_locale(request: Request) -> Locale:
    """FastAPI dependency: the language of this request."""
    return negotiate(request.headers.get("accept-language"))


def t(locale: Locale, key: str, **vars: object) -> str:
    """The text for ``key`` in ``locale``; French then the key itself as fallbacks."""
    text = _DICT[locale].get(key) or _FR.get(key) or key
    return text.format(**vars) if vars else text


def keys() -> dict[Locale, set[str]]:
    """Every key per language — the test that English mirrors French reads this."""
    return {"fr": set(_FR), "en": set(_EN)}


__all__ = [
    "DEFAULT_LOCALE",
    "LOCALES",
    "Locale",
    "as_locale",
    "current_locale",
    "keys",
    "negotiate",
    "t",
]
