"""Bank aggregator abstraction layer (ADR-008, Phase A).

Goal: isolate vendor-specific code (Powens, future Bridge/Plaid/...) behind
a stable interface so swapping providers later doesn't require deep refactor.

Public API:
- IBankAggregator : Protocol any provider must implement
- BankAccount, Investment, Transaction, SyncResult : neutral DTOs
- AccountType : enum of supported account types
"""

from .interface import IBankAggregator
from .types import (
    AccountType,
    BankAccount,
    Investment,
    SyncResult,
    Transaction,
)

__all__ = [
    "AccountType",
    "BankAccount",
    "IBankAggregator",
    "Investment",
    "SyncResult",
    "Transaction",
]
