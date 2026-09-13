"""« La liste de l'année » is computed by the scheduler and served from a file."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.errors import DataSourceError
from app.finance import picks
from app.models import PicksResponse, PicksTrackRecord


def _response(computed_at: datetime) -> PicksResponse:
    return PicksResponse(
        computed_at=computed_at.isoformat(timespec="seconds"),
        as_of="2026-09-12",
        next_review="2026-12-31",
        review="quarterly",
        guard_on=False,
        held=["ASML.AS"],
        bought=["ASML.AS"],
        sold=[],
        universe_size=1,
        indices=["stoxx_europe_600"],
        top=30,
        track_record=PicksTrackRecord(
            since="2010-01-31",
            cagr=0.1,
            universe_cagr=0.05,
            max_drawdown=-0.3,
            universe_max_drawdown=-0.4,
            turnover=0.2,
            reviews=60,
            guarded_reviews=4,
            yearly=[],
        ),
    )


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(picks, "_PATH", tmp_path / "picks.json")
    return tmp_path / "picks.json"


def test_nothing_stored_means_nothing_served(store):
    assert picks.load() is None
    assert not picks.is_fresh()


def test_refresh_writes_what_load_reads_back(store, monkeypatch):
    fresh = _response(datetime.now(UTC))
    monkeypatch.setattr(picks, "build", lambda: fresh)

    picks.refresh()

    assert store.exists()
    assert picks.load() == fresh
    assert picks.is_fresh()


def test_a_stale_list_is_recomputed_and_a_fresh_one_is_kept(store, monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        picks, "build", lambda: calls.append("built") or _response(datetime.now(UTC))
    )

    store.write_text(_response(datetime.now(UTC) - timedelta(days=2)).model_dump_json())
    picks.refresh_if_stale()
    picks.refresh_if_stale()

    assert calls == ["built"]


def test_an_unreachable_source_keeps_the_last_list(store, monkeypatch):
    last = _response(datetime.now(UTC) - timedelta(days=2))
    store.write_text(last.model_dump_json())

    def _fail():
        raise DataSourceError("Yahoo injoignable")

    monkeypatch.setattr(picks, "build", _fail)

    picks.refresh_if_stale()  # logs, does not raise

    assert picks.load() == last


def test_an_unreadable_file_is_a_miss(store):
    store.write_text("{not json")

    assert picks.load() is None
