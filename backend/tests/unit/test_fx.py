"""Amounts in another currency read in euros at the ECB reference rate (ADR-038)."""

from __future__ import annotations

import pandas as pd
import pytest

from app.errors import DataSourceError
from app.finance import fx


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setattr(fx, "_LAST_KNOWN", {})


def _ecb(rates: dict[str, float], calls: list[str] | None = None):
    def series(key: str, *, start=None, last_n=None):
        if calls is not None:
            calls.append(key)
        ccy = key.split(".")[1]
        if ccy not in rates:
            raise DataSourceError(f"{key} a répondu 404.")
        return pd.Series([rates[ccy]], index=pd.to_datetime(["2026-10-26"]))

    return series


async def test_euros_never_call_the_ecb(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(fx.ecb, "series", _ecb({}, calls))

    assert await fx.to_eur_factors(["EUR", None, "eur"]) == {"EUR": 1.0}
    assert calls == []


async def test_a_currency_reads_at_one_over_the_rate(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(fx.ecb, "series", _ecb({"SGD": 1.4327, "USD": 1.1188}, calls))

    factors = await fx.to_eur_factors(["SGD", "sgd", "USD", "EUR"])

    assert factors["SGD"] == pytest.approx(1 / 1.4327)
    assert factors["USD"] == pytest.approx(1 / 1.1188)
    assert calls == ["EXR/D.SGD.EUR.SP00.A", "EXR/D.USD.EUR.SP00.A"]


async def test_a_currency_without_rate_is_left_out(monkeypatch):
    monkeypatch.setattr(fx.ecb, "series", _ecb({}))

    assert await fx.to_eur_factors(["VND", "not a code"]) == {"EUR": 1.0}


def test_the_last_rate_read_serves_when_the_ecb_is_down(monkeypatch):
    monkeypatch.setattr(fx.ecb, "series", _ecb({"SGD": 1.43}))
    assert fx.eur_rate("SGD") == 1.43

    monkeypatch.setattr(fx.ecb, "series", _ecb({}))
    assert fx.eur_rate("SGD") == 1.43
    assert fx.eur_rate("HKD") is None
