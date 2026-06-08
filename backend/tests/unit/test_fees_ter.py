"""Unit tests for fees.apply_ter_to_fee_fn (ADR-021)."""

from __future__ import annotations

from app.finance.fees import apply_ter_to_fee_fn


def test_zero_ter_returns_input_function() -> None:
    """weighted_ter=0 → wrap is a no-op (returns the input function unchanged)."""

    def broker_fee(value: float) -> float:
        return 10.0 + value * 0.001

    wrapped = apply_ter_to_fee_fn(broker_fee, weighted_ter=0.0)
    assert wrapped is broker_fee


def test_negative_ter_returns_input_function() -> None:
    """Defensive: negative TER → no-op rather than crediting fees."""

    def broker_fee(value: float) -> float:
        return 5.0

    wrapped = apply_ter_to_fee_fn(broker_fee, weighted_ter=-0.01)
    assert wrapped is broker_fee


def test_ter_adds_monthly_proportional_cost() -> None:
    """Combined fee = broker_fee(value) + value * ter / 12."""

    def broker_fee(value: float) -> float:
        return 10.0

    wrapped = apply_ter_to_fee_fn(broker_fee, weighted_ter=0.0024)

    # value = 12_000 €, TER = 0.24%/an → monthly TER cost = 12_000 * 0.0024 / 12 = 2.4 €
    # Combined = 10 + 2.4 = 12.4 €
    assert wrapped(12_000) == 12.4


def test_ter_scales_with_value() -> None:
    """Fee scales linearly with portfolio value."""

    def broker_fee(value: float) -> float:
        return 0.0

    wrapped = apply_ter_to_fee_fn(broker_fee, weighted_ter=0.006)  # 0.6%/an

    # At 10 000 € → 5 €/mois.  At 100 000 € → 50 €/mois.
    assert wrapped(10_000) == 10_000 * 0.006 / 12
    assert wrapped(100_000) == 100_000 * 0.006 / 12
    # Ratio is exactly 10
    assert wrapped(100_000) / wrapped(10_000) == 10
