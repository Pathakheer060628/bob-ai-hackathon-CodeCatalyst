"""Tests for the SQLAlchemy-backed run persistence layer.

Uses a temporary SQLite file (not the real gridsentinel.db) so these tests
never touch the app's actual local run history.
"""

from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from backend.api.db import init_db, make_engine
from backend.api.run_store import RunStore
from backend.tools.load_balancing import LoadBalanceConfig


def _store_at(db_path) -> RunStore:
    engine = make_engine(f"sqlite:///{db_path}")
    init_db(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return RunStore(session_factory=session_factory)


def test_create_and_get_run(tmp_path):
    store = _store_at(tmp_path / "runs.db")
    record = store.create(window_end="2019-06-30T23:00:00", lookback_days=30, horizon_hours=24)

    assert record.status == "pending"
    fetched = store.get(record.run_id)
    assert fetched is not None
    assert fetched.run_id == record.run_id
    assert fetched.window_end == "2019-06-30T23:00:00"
    assert fetched.lookback_days == 30
    assert fetched.horizon_hours == 24
    assert fetched.result is None
    assert fetched.progress_log == []


def test_create_persists_load_balance_config(tmp_path):
    store = _store_at(tmp_path / "runs.db")
    config = LoadBalanceConfig(
        dispatchable_capacity_mw=5000.0,
        storage_capacity_mwh=400.0,
        storage_max_rate_mw=200.0,
        storage_efficiency=0.85,
        storage_initial_soc_mwh=200.0,
        max_demand_response_fraction=0.1,
    )
    record = store.create(
        window_end="2019-01-01T00:00:00", lookback_days=14, horizon_hours=12, load_balance_config=config
    )
    fetched = store.get(record.run_id)
    assert isinstance(fetched.load_balance_config, LoadBalanceConfig)
    assert fetched.load_balance_config.dispatchable_capacity_mw == 5000.0
    assert fetched.load_balance_config.storage_efficiency == 0.85


def test_status_transitions_and_progress_log(tmp_path):
    store = _store_at(tmp_path / "runs.db")
    record = store.create(window_end="2019-06-30T23:00:00", lookback_days=30, horizon_hours=24)

    store.mark_running(record.run_id)
    assert store.get(record.run_id).status == "running"

    store.append_progress(record.run_id, "forecast: computed 24h horizon")
    store.append_progress(record.run_id, "anomalies: found 2 episodes")
    fetched = store.get(record.run_id)
    assert fetched.progress_log == [
        "forecast: computed 24h horizon",
        "anomalies: found 2 episodes",
    ]

    store.mark_done(record.run_id, {"narrative": "ok", "verification": {"trusted": True}})
    fetched = store.get(record.run_id)
    assert fetched.status == "done"
    assert fetched.result["verification"]["trusted"] is True


def test_mark_error(tmp_path):
    store = _store_at(tmp_path / "runs.db")
    record = store.create(window_end="2019-06-30T23:00:00", lookback_days=30, horizon_hours=24)
    store.mark_error(record.run_id, "boom")
    fetched = store.get(record.run_id)
    assert fetched.status == "error"
    assert fetched.error == "boom"


def test_get_unknown_run_returns_none(tmp_path):
    store = _store_at(tmp_path / "runs.db")
    assert store.get("does-not-exist") is None


def test_list_recent_orders_newest_first(tmp_path):
    store = _store_at(tmp_path / "runs.db")
    first = store.create(window_end="2019-01-01T00:00:00", lookback_days=7, horizon_hours=24)
    second = store.create(window_end="2019-02-01T00:00:00", lookback_days=7, horizon_hours=24)

    recent = store.list_recent(limit=10)
    ids = [r.run_id for r in recent]
    assert second.run_id in ids and first.run_id in ids
    # newest (highest created_at) should come first
    assert ids.index(second.run_id) <= ids.index(first.run_id)


def test_run_survives_fresh_repository_pointed_at_same_db_file(tmp_path):
    """The core persistence guarantee: a new RunStore/engine instance pointed
    at the same SQLite file can read runs created by a previous instance --
    i.e. runs survive a process/server restart."""
    db_path = tmp_path / "shared_runs.db"

    store_a = _store_at(db_path)
    record = store_a.create(window_end="2019-06-30T23:00:00", lookback_days=30, horizon_hours=24)
    store_a.mark_done(record.run_id, {"narrative": "done", "verification": {"trusted": True}})

    # Fresh engine/session factory/repository, same underlying file.
    engine_b = make_engine(f"sqlite:///{db_path}")
    session_factory_b = sessionmaker(bind=engine_b, autoflush=False, autocommit=False, future=True)
    store_b = RunStore(session_factory=session_factory_b)

    fetched = store_b.get(record.run_id)
    assert fetched is not None
    assert fetched.status == "done"
    assert fetched.result["narrative"] == "done"
