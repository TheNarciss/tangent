"""The month arithmetic behind the spending window."""

from datetime import date

from app.routers.spending import _shift


def test_shifting_back_crosses_the_year():
    assert _shift(date(2026, 2, 1), -3) == date(2025, 11, 1)


def test_shifting_forward_crosses_the_year():
    assert _shift(date(2026, 11, 1), 2) == date(2027, 1, 1)


def test_zero_is_the_same_month():
    assert _shift(date(2026, 9, 1), 0) == date(2026, 9, 1)
