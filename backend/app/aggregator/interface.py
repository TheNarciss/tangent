"""Protocol any bank aggregator implementation must satisfy.

Python `Protocol` (structural subtyping) rather than abstract base class,
to allow drop-in mock implementations in tests without forcing inheritance.

All methods are async — bank APIs are I/O bound and must not block the event loop.

Cf ADR-008.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .types import BankAccount, Investment, SyncResult, Transaction


@runtime_checkable
class IBankAggregator(Protocol):
    """A bank aggregator (Powens, Bridge, Plaid, etc.).

    Implementations should be instantiated PER-USER with the user's
    decrypted token. No global mutable state (cf ADR-019).
    """

    @property
    def provider_name(self) -> str:
        """Lowercase identifier of the provider, e.g. 'powens'."""
        ...

    async def get_accounts(self) -> list[BankAccount]:
        """Fetch every account the user has connected (all types)."""
        ...

    async def get_investments(self, account_id: str) -> list[Investment]:
        """Fetch holdings inside an investment account."""
        ...

    async def get_transactions(
        self,
        account_id: str,
        limit: int = 100,
    ) -> list[Transaction]:
        """Fetch the most recent transactions for an account."""
        ...

    async def sync(self) -> SyncResult:
        """End-to-end sync: pull everything from the provider and return a normalized result.

        The caller is responsible for persisting the result to DB.
        """
        ...

    async def handle_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process an incoming webhook from the provider."""
        ...
