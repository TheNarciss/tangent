"""Powens implementation of IBankAggregator (Phase A skeleton).

For now this is a thin wrapper around the existing `sync_portfolio()` in
app.powens.sync. As Phase A1 progresses, get_accounts / get_investments /
get_transactions will be filled in with full Powens → DTO mapping.

Constructor takes a decrypted user token (cf ADR-019: no global mutable state).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..aggregator import (
    BankAccount,
    Investment,
    Transaction,
)
from ..aggregator import (
    SyncResult as AggregatorSyncResult,
)
from .sync import sync_portfolio


class PowensAggregator:
    """Implements IBankAggregator for the Powens provider."""

    provider_name: str = "powens"

    def __init__(
        self,
        *,
        token: str,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> None:
        self._token = token
        self._user_id = user_id
        self._session = session

    # ── IBankAggregator methods (skeleton) ─────────────────────────────────

    async def get_accounts(self) -> list[BankAccount]:
        """TODO Phase A1: full Powens → BankAccount mapping for all types.

        Today only PEA is mapped via sync_portfolio(). Will expose checking,
        savings, life insurance, etc.
        """
        raise NotImplementedError("Phase A1 todo")

    async def get_investments(self, account_id: str) -> list[Investment]:
        raise NotImplementedError("Phase A1 todo")

    async def get_transactions(
        self,
        account_id: str,
        limit: int = 100,
    ) -> list[Transaction]:
        raise NotImplementedError("Phase A1 todo")

    async def sync(self) -> AggregatorSyncResult:
        """Pull from Powens and return a normalized SyncResult.

        Phase A skeleton: delegates to existing sync_portfolio() and adapts
        the return value shell. Detailed Position → Investment mapping comes
        in Phase A1. Callers should keep using sync_portfolio() directly for
        portfolio persistence until the migration is complete.
        """
        powens_result = await sync_portfolio(
            token=self._token,
            user_id=self._user_id,
            session=self._session,
        )

        return AggregatorSyncResult(
            success=powens_result.success,
            provider=self.provider_name,
            accounts=[],  # TODO Phase A1
            investments=[],  # TODO Phase A1
            transactions=[],  # TODO Phase A1
            error=powens_result.error,
            synced_at=powens_result.synced_at,
        )

    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Powens webhook handler — currently disabled (cf ADR-019).

        Phase A2: re-enable once we have powens_user_id mapping in DB.
        """
        from .webhooks import handle_webhook as _handle

        return await _handle(payload)
