"""Shared HTTP access for the external sources, with a process-local TTL cache.

Every source goes through here so timeout, User-Agent and caching behave the
same everywhere. The cache lives in the process: a restart refetches, which is
what we want for series that get revised (Eurostat and FRED both restate).

Failures surface as `DataSourceError` — a 502 for the caller, never a raw
network exception leaking into a route.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from ..errors import DataSourceError
from .config import config

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[datetime, Any]] = {}


def clear_cache() -> None:
    """Drop every cached response. Used by tests and by the probe CLI."""
    _CACHE.clear()


def _cached(key: str, ttl_hours: float) -> Any | None:
    hit = _CACHE.get(key)
    if hit and datetime.now() - hit[0] < timedelta(hours=ttl_hours):
        logger.debug("data cache hit: %s", key)
        return hit[1]
    return None


def _store(key: str, value: Any) -> None:
    _CACHE[key] = (datetime.now(), value)


def _headers() -> dict[str, str]:
    return {"User-Agent": config().user_agent}


def get_text(url: str, *, params: dict[str, str] | None = None, ttl_hours: float) -> str:
    """GET a text body (CSV, JSON). Cached under url + params."""
    key = f"GET:{url}:{sorted((params or {}).items())}"
    hit = _cached(key, ttl_hours)
    if hit is not None:
        return str(hit)

    body = _request("GET", url, params=params).text
    _store(key, body)
    return body


def get_bytes(url: str, *, ttl_hours: float) -> bytes:
    """GET a binary body (zip archives). Cached under url."""
    key = f"GETB:{url}"
    hit = _cached(key, ttl_hours)
    if hit is not None:
        return bytes(hit)

    body = _request("GET", url).content
    _store(key, body)
    return body


def post_json(url: str, payload: Any, *, ttl_hours: float) -> Any:
    """POST a JSON body and decode the JSON answer. Cached under url + payload."""
    key = f"POST:{url}:{payload!r}"
    hit = _cached(key, ttl_hours)
    if hit is not None:
        return hit

    response = _request("POST", url, json=payload)
    try:
        decoded = response.json()
    except ValueError as exc:
        raise DataSourceError(f"Réponse non-JSON de {url}: {exc}") from exc
    _store(key, decoded)
    return decoded


def _request(method: str, url: str, **kwargs: Any) -> httpx.Response:
    try:
        response = httpx.request(
            method,
            url,
            timeout=config().http_timeout_seconds,
            headers=_headers(),
            follow_redirects=True,
            **kwargs,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise DataSourceError(f"{url} a répondu {exc.response.status_code}.") from exc
    except httpx.HTTPError as exc:
        raise DataSourceError(f"Échec de l'appel à {url}: {exc}") from exc
    return response
