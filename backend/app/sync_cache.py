"""In-process cache for /accounts/sync results.

Per-user, with TTL (5 min by default). Avoids hitting Powens on every page mount.
Lost on backend restart — that's fine, the next call just re-syncs (transparent).

Doubles as the rate-limit mechanism: if a fresh entry exists (< TTL), the cached
response is returned immediately without re-running the sync. So even if the
user clicks "Synchroniser" 10 times in a row, only the first one actually hits
Powens.

To force a real sync (bypass cache), use sync_cache.invalidate(user_id) before
calling the sync logic. The /accounts/refresh endpoint does exactly this.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Cache TTL in seconds. 5 min is a reasonable default — long enough to absorb
# typical user navigation (open Accounts tab, switch back and forth) without
# spamming Powens, short enough to feel fresh.
SYNC_CACHE_TTL_SECONDS = 5 * 60


class _SyncCache:
    """Async-safe per-user sync result cache with TTL.

    Backed by a plain dict + asyncio.Lock. Single-process only (no Redis).
    For a multi-worker setup, replace with a shared cache (Redis, memcached).
    """

    def __init__(self) -> None:
        self._store: dict[uuid.UUID, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_fresh(self, user_id: uuid.UUID) -> Any | None:
        """Return cached value if still fresh (< TTL), else None.

        Stale entries are NOT removed eagerly — they get overwritten on the
        next set(). Memory cost is bounded by number of active users.
        """
        async with self._lock:
            entry = self._store.get(user_id)
            if entry is None:
                return None
            timestamp, value = entry
            age = time.monotonic() - timestamp
            if age > SYNC_CACHE_TTL_SECONDS:
                return None
            logger.debug("sync_cache hit user=%s (age=%.1fs)", user_id, age)
            return value

    async def set(self, user_id: uuid.UUID, value: Any) -> None:
        """Store value with current timestamp."""
        async with self._lock:
            self._store[user_id] = (time.monotonic(), value)

    async def invalidate(self, user_id: uuid.UUID) -> None:
        """Remove entry for user — next call will re-sync against Powens."""
        async with self._lock:
            self._store.pop(user_id, None)


# Module-level singleton — imported by routers
sync_cache = _SyncCache()
