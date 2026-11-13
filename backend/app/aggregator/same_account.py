"""Which provider ids are one bank account, and which connections bring nothing.

Powens numbers accounts per connection: a bank connected again brings the
same accounts back under new ids, next to the old ones it still lists.
Enable Banking's ids already survive a new consent (`identification_hash`),
so only Powens listings are matched here.

An account is known by its IBAN, else by its number at its bank, with its
kind and currency. Only accounts of different connections can be one: a bank
never lists an account twice in one connection, so two look-alikes there
(two loans whose masked numbers end alike) are two accounts, and nothing of
theirs is merged.
"""

from __future__ import annotations

from collections import Counter

from .types import BankAccount

_IDS_PER_CONNECTION = frozenset({"powens"})


def row_identity(
    kind: str, currency: str, iban: str | None, number: str | None, bank: str | None
) -> tuple[str, ...] | None:
    """What says two ids are one account: its IBAN, else its number at its bank.

    The kind and the currency go with it: a card is not its current account,
    and a multi-currency account can share one IBAN between its pockets.
    """
    if iban and iban.strip():
        return ("iban", kind, currency, "".join(iban.split()).upper())
    if number and number.strip():
        return ("number", kind, currency, (bank or "").casefold(), "".join(number.split()).upper())
    return None


def identity(account: BankAccount) -> tuple[str, ...] | None:
    """The account behind a provider id, for the providers whose ids change; else None."""
    if account.provider not in _IDS_PER_CONNECTION:
        return None
    return row_identity(
        account.type.value, account.currency, account.iban, account.number, account.institution_name
    )


def connection(raw_data: dict | None) -> object:
    """The connection a listing comes from (Powens `id_connection`), None if unknown."""
    return (raw_data or {}).get("id_connection")


def distinct_connections(connections: list[object]) -> bool:
    """Whether the look-alikes each come from their own connection: then they are one account."""
    return None not in connections and len(set(connections)) == len(connections)


def _works(account: BankAccount) -> bool:
    """Its connection reads the bank: read once, no error. Unknown is not working."""
    return (account.raw_data or {}).get("connection_works") is True


def _number(value: object) -> int:
    text = "" if value is None else str(value)
    return int(text) if text.isdigit() else -1


def _rank(account: BankAccount) -> tuple[bool, int, int]:
    """The listing to keep: one that works, then the newest connection, then the newest id."""
    return (
        _works(account),
        _number(connection(account.raw_data)),
        _number(account.provider_account_id),
    )


def one_per_account(accounts: list[BankAccount]) -> list[BankAccount]:
    """A bank connected twice lists its accounts twice: keep one listing of each.

    The kept one comes from a connection that works, the newest of them: the
    access set up last and read without error. Always the same one from a
    sync to the next, so an account does not swing between two connections.
    Order is kept.
    """
    groups: dict[tuple[str, ...], list[BankAccount]] = {}
    for acc in accounts:
        key = identity(acc)
        if key is not None:
            groups.setdefault(key, []).append(acc)
    dropped: set[int] = set()
    for group in groups.values():
        if len(group) > 1 and distinct_connections([connection(a.raw_data) for a in group]):
            kept = max(group, key=_rank)
            dropped.update(id(a) for a in group if a is not kept)
    return [acc for acc in accounts if id(acc) not in dropped]


def redundant_connections(accounts: list[BankAccount]) -> set[object]:
    """The connections whose every account a newer connection that works also lists.

    They bring nothing: removing them loses no account and no history. A
    connection still importing, one that works where the newer one does not,
    or one with a single account the newer one lacks (a loan only the old
    access sees) brings something, and stays.
    """
    kept = one_per_account(accounts)
    counts = Counter(identity(a) for a in kept)
    winners = {key: a for a in kept if (key := identity(a)) is not None and counts[key] == 1}

    def covered(acc: BankAccount, conn: object) -> bool:
        key = identity(acc)
        winner = winners.get(key) if key is not None else None
        return (
            winner is not None
            and winner is not acc
            and _works(winner)
            and _number(connection(winner.raw_data)) > _number(conn)
        )

    by_connection: dict[object, list[BankAccount]] = {}
    for acc in accounts:
        by_connection.setdefault(connection(acc.raw_data), []).append(acc)
    return {
        conn
        for conn, listed in by_connection.items()
        if conn is not None and all(covered(acc, conn) for acc in listed)
    }
