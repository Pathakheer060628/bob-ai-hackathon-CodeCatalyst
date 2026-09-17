"""FastAPI app: dataset info, run creation, SSE progress streaming, PDF export."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from backend.agents.orchestrator import PipelineRequest, stream_pipeline
from backend.api.db import init_db
from backend.api.run_store import run_store
from backend.api.schemas import (
    RunCreateRequest,
    serialize_run_result,
    serialize_run_summary,
    to_load_balance_config,
)
from backend.data.loader import data_bounds, load_grid_data
from backend.reports.pdf_export import build_pdf_report

@asynccontextmanager
async def _lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="GridSentinel API", version="0.1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/dataset/info")
def dataset_info():
    start, end = data_bounds()
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "source": "Open Power System Data (ENTSO-E), Germany, hourly, 2017-2019",
        "license": "CC-BY 4.0",
    }


def _resolve_window(payload: RunCreateRequest):
    full_history = load_grid_data()
    window_end = pd.Timestamp(payload.window_end)
    if window_end.tzinfo is None:
        window_end = window_end.tz_localize("UTC")
    window_start = window_end - pd.Timedelta(days=payload.lookback_days)

    min_ts, max_ts = data_bounds()
    if window_end > pd.Timestamp(max_ts) or window_start < pd.Timestamp(min_ts):
        raise HTTPException(
            status_code=400,
            detail=f"Requested window [{window_start}, {window_end}] falls outside dataset "
            f"range [{min_ts}, {max_ts}].",
        )

    history = full_history.loc[window_start:window_end]
    return full_history, history


@app.post("/api/runs")
def create_run(payload: RunCreateRequest):
    _, history = _resolve_window(payload)
    peak_load = float(history["load_actual_mw"].max())
    config = to_load_balance_config(payload.load_balance_config, peak_load)

    record = run_store.create(
        window_end=payload.window_end,
        lookback_days=payload.lookback_days,
        horizon_hours=payload.horizon_hours,
        load_balance_config=config,
    )
    return {"run_id": record.run_id, "status": record.status}


@app.get("/api/runs")
def list_runs(limit: int = 25):
    records = run_store.list_recent(limit=limit)
    return {"runs": [serialize_run_summary(r) for r in records]}


@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str):
    record = run_store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        run_store.mark_running(run_id)
        payload = RunCreateRequest(
            window_end=record.window_end,
            lookback_days=record.lookback_days,
            horizon_hours=record.horizon_hours,
        )
        try:
            full_history, history = _resolve_window(payload)
            request = PipelineRequest(
                history=history,
                full_history=full_history,
                horizon_hours=record.horizon_hours,
                load_balance_config=record.load_balance_config,
            )

            final_state: dict = {}
            for node_name, update in stream_pipeline(request):
                final_state.update(update)
                for line in update.get("progress_log", []):
                    run_store.append_progress(run_id, line)
                    yield {
                        "event": "progress",
                        "data": json.dumps({"node": node_name, "message": line}),
                    }

            result = serialize_run_result(final_state)
            run_store.mark_done(run_id, result)
            yield {"event": "result", "data": json.dumps(result)}
        except Exception as exc:  # surface pipeline errors to the SSE client rather than hanging it
            run_store.mark_error(run_id, str(exc))
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}

    return EventSourceResponse(event_generator())


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    record = run_store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": record.run_id,
        "status": record.status,
        "result": record.result,
        "error": record.error,
    }


@app.get("/api/runs/{run_id}/report.pdf")
def get_run_report(run_id: str):
    record = run_store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if record.status != "done" or record.result is None:
        raise HTTPException(status_code=409, detail="Run is not complete yet")

    pdf_bytes = build_pdf_report(record.run_id, record.result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="gridsentinel_brief_{run_id}.pdf"'},
    )
