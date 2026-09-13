"""Yahoo batches are cached twelve hours, in memory and on disk."""

from __future__ import annotations

import os
import time

import pandas as pd
import pytest

from app.finance import market

_REAL_FETCH = market.fetch_prices  # captured before the conftest cuts Yahoo off


@pytest.fixture
def disk(tmp_path, monkeypatch):
    monkeypatch.setattr(market, "fetch_prices", _REAL_FETCH)
    monkeypatch.setattr(market, "_DIR", tmp_path)
    market._CACHE.clear()
    yield tmp_path
    market._CACHE.clear()


def _fake_download(calls: list[int]):
    def run(tickers, period, auto_adjust, progress):
        calls.append(1)
        index = pd.bdate_range("2026-01-01", periods=5)
        return pd.DataFrame({("Close", "CW8.PA"): [100.0, 101, 102, 103, 104]}, index=index)

    return run


def test_a_restart_reads_the_batch_from_disk(disk, monkeypatch):
    calls: list[int] = []
    monkeypatch.setattr(market.yf, "download", _fake_download(calls))

    first = market.fetch_prices(["CW8.PA"], period="1mo")
    market._CACHE.clear()  # the process restarted
    second = market.fetch_prices(["CW8.PA"], period="1mo")

    assert calls == [1]
    pd.testing.assert_frame_equal(first, second)
    assert list(disk.glob("*.pkl"))


def test_a_stale_file_is_refetched(disk, monkeypatch):
    calls: list[int] = []
    monkeypatch.setattr(market.yf, "download", _fake_download(calls))

    market.fetch_prices(["CW8.PA"], period="1mo")
    old = time.time() - 13 * 3600
    for path in disk.glob("*.pkl"):
        os.utime(path, (old, old))
    market._CACHE.clear()
    market.fetch_prices(["CW8.PA"], period="1mo")

    assert calls == [1, 1]


def test_an_unwritable_directory_is_only_a_warning(tmp_path, monkeypatch):
    calls: list[int] = []
    monkeypatch.setattr(market, "fetch_prices", _REAL_FETCH)
    monkeypatch.setattr(market.yf, "download", _fake_download(calls))
    monkeypatch.setattr(market, "_DIR", tmp_path / "file-not-dir")
    (tmp_path / "file-not-dir").write_text("in the way")
    market._CACHE.clear()

    prices = market.fetch_prices(["CW8.PA"], period="1mo")

    assert len(prices) == 5
    market._CACHE.clear()
