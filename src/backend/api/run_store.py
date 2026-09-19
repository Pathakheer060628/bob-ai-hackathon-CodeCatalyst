"""Run persistence backed by SQLite (via SQLAlchemy).

Runs now survive a server restart. The public surface intentionally mirrors
the old in-memory implementation (`RunRecord` dataclass, `RunStore` with
`create` / `get` / `mark_running` / `mark_done` / `mark_error`, and a module
level `run_store` singleton) so `backend/api/main.py` and the SSE streaming
logic didn't need invasive changes -- only the storage underneath changed.
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.agents.orchestrator import ScenarioConfig
from backend.api.db import SessionLocal, init_db
from backend.api.models import Run
from backend.tools.load_balancing import LoadBalanceConfig


@dataclass
class RunRecord:
    run_id: str
    status: str  # "pending" | "running" | "done" | "error"
    created_at: datetime
    window_end: str
    lookback_days: int
    horizon_hours: int
    forecast_model: str = "seasonal"
    load_balance_config: Any = None
    scenario: ScenarioConfig | None = None
    result: dict | None = None
    progress_log: list = field(default_factory=list)
    error: str | None = None


def _config_to_dict(config: LoadBalanceConfig | None) -> dict | None:
    if config is None:
        return None
    return dataclasses.asdict(config)


def _config_from_dict(payload: dict | None) -> LoadBalanceConfig | None:
    if payload is None:
        return None
    return LoadBalanceConfig(**payload)


def _scenario_to_dict(scenario: ScenarioConfig | None) -> dict | None:
    if scenario is None:
        return None
    return dataclasses.asdict(scenario)


def _scenario_from_dict(payload: dict | None) -> ScenarioConfig | None:
    if payload is None:
        return None
    return ScenarioConfig(**payload)


def _row_to_record(row: Run) -> RunRecord:
    return RunRecord(
        run_id=row.id,
        status=row.status,
        created_at=row.created_at,
        window_end=row.window_end,
        lookback_days=row.lookback_days,
        horizon_hours=row.horizon_hours,
        forecast_model=row.forecast_model,
        load_balance_config=_config_from_dict(row.config),
        scenario=_scenario_from_dict(row.scenario),
        result=row.result,
        progress_log=list(row.progress_log or []),
        error=row.error,
    )


class RunStore:
    """SQLAlchemy-backed repository for run records.

    Each call opens and closes its own short-lived session -- there's no
    long-running unit-of-work here, just simple CRUD against a local SQLite
    file, which keeps this safe to share across the sync request handlers
    and the SSE generator without extra locking.
    """

    def __init__(self, session_factory=None) -> None:
        self._session_factory = session_factory or SessionLocal

    def _session(self) -> Session:
        return self._session_factory()

    def create(
        self,
        window_end: str,
        lookback_days: int,
        horizon_hours: int,
        forecast_model: str = "seasonal",
        load_balance_config: LoadBalanceConfig | None = None,
        scenario: ScenarioConfig | None = None,
    ) -> RunRecord:
        run_id = uuid.uuid4().hex[:12]
        with self._session() as session:
            row = Run(
                id=run_id,
                status="pending",
                created_at=datetime.now(timezone.utc),
                window_end=window_end,
                lookback_days=lookback_days,
                horizon_hours=horizon_hours,
                forecast_model=forecast_model,
                config=_config_to_dict(load_balance_config),
                scenario=_scenario_to_dict(scenario),
                result=None,
                progress_log=[],
                error=None,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return _row_to_record(row)

    def get(self, run_id: str) -> RunRecord | None:
        with self._session() as session:
            row = session.get(Run, run_id)
            return _row_to_record(row) if row is not None else None

    def list_recent(self, limit: int = 25) -> list[RunRecord]:
        with self._session() as session:
            # created_at alone isn't a reliable sort key: two runs created in rapid
            # succession (e.g. back-to-back API calls) can land on the same
            # microsecond-resolution timestamp. SQLite's implicit rowid always
            # increases with insertion order, so it's used as a tiebreaker to keep
            # "most recent first" deterministic even when timestamps tie.
            rows = (
                session.query(Run)
                .order_by(Run.created_at.desc(), text("rowid DESC"))
                .limit(limit)
                .all()
            )
            return [_row_to_record(r) for r in rows]

    def mark_running(self, run_id: str) -> None:
        with self._session() as session:
            row = session.get(Run, run_id)
            if row is not None:
                row.status = "running"
                session.commit()

    def append_progress(self, run_id: str, message: str) -> None:
        with self._session() as session:
            row = session.get(Run, run_id)
            if row is not None:
                row.progress_log = [*(row.progress_log or []), message]
                session.commit()

    def mark_done(self, run_id: str, result: dict) -> None:
        with self._session() as session:
            row = session.get(Run, run_id)
            if row is not None:
                row.status = "done"
                row.result = result
                session.commit()

    def mark_error(self, run_id: str, error: str) -> None:
        with self._session() as session:
            row = session.get(Run, run_id)
            if row is not None:
                row.status = "error"
                row.error = error
                session.commit()


init_db()
run_store = RunStore()
