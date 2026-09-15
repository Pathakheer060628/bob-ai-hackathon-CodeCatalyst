"""In-memory run store.

Correct for this demo; a real multi-user/persistent deployment would back
this with a database instead. Each run is created in "pending" state by
POST /api/runs and transitions to "done" once its SSE stream finishes
executing the pipeline.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RunRecord:
    run_id: str
    status: str  # "pending" | "running" | "done" | "error"
    created_at: datetime
    window_end: str
    lookback_days: int
    horizon_hours: int
    load_balance_config: Any = None
    result: dict | None = None
    error: str | None = None


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    def create(self, window_end: str, lookback_days: int, horizon_hours: int, load_balance_config=None) -> RunRecord:
        run_id = uuid.uuid4().hex[:12]
        record = RunRecord(
            run_id=run_id,
            status="pending",
            created_at=datetime.now(timezone.utc),
            window_end=window_end,
            lookback_days=lookback_days,
            horizon_hours=horizon_hours,
            load_balance_config=load_balance_config,
        )
        self._runs[run_id] = record
        return record

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def mark_running(self, run_id: str) -> None:
        if run_id in self._runs:
            self._runs[run_id].status = "running"

    def mark_done(self, run_id: str, result: dict) -> None:
        if run_id in self._runs:
            self._runs[run_id].status = "done"
            self._runs[run_id].result = result

    def mark_error(self, run_id: str, error: str) -> None:
        if run_id in self._runs:
            self._runs[run_id].status = "error"
            self._runs[run_id].error = error


run_store = RunStore()
