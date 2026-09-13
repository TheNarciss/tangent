"""The month arithmetic behind the spending window."""

from datetime import date

from app.routers.spending import _shift


def test_shifting_back_crosses_the_year():
    assert _shift(date(2026, 2, 1), -3) == date(2025, 11, 1)


def test_shifting_forward_crosses_the_year():
    assert _shift(date(2026, 11, 1), 2) == date(2027, 1, 1)


def test_zero_is_the_same_month():
    assert _shift(date(2026, 9, 1), 0) == date(2026, 9, 1)


# ── Les libellés de la banque, repliés par marchand ─────────────────────────

from app.routers.spending import _merchants  # noqa: E402


def test_visits_to_the_same_shop_fold_together():
    rows = [
        ("CB CARREFOUR 12/09", 40.0, 1),
        ("CB CARREFOUR 03/09", 25.5, 1),
        ("PRLV SEPA FREE MOBILE 123456", 19.99, 1),
    ]

    out = _merchants(rows)

    assert [(m.name, m.total, m.count) for m in out] == [
        ("carrefour", 65.5, 2),
        ("free mobile", 19.99, 1),
    ]


def test_the_list_is_capped_and_ordered_largest_first():
    rows = [(f"SHOP {i}", float(i), 1) for i in range(1, 15)]

    out = _merchants(rows, top=3)

    assert len(out) == 1  # « SHOP 1 » … « SHOP 14 » are one shop once the digits go
    assert out[0].name == "shop"
    assert out[0].count == 14
