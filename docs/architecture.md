# Architecture

## Components

```
src/
├── backend/
│   ├── data/
│   │   ├── grid_renewable_de_2017_2019.csv   # real OPSD/ENTSO-E extract
│   │   ├── loader.py                          # cached DataFrame + derived columns
│   │   └── build_dataset.py                   # regenerates the CSV from raw OPSD
│   ├── tools/                                  # deterministic, typed, unit-tested
│   │   ├── forecasting.py                      # demand + renewable supply forecast
│   │   ├── anomaly_detection.py                # CUSUM anomaly episodes per asset
│   │   ├── root_cause.py                       # rule-based root-cause classifier
│   │   ├── load_balancing.py                   # LP: dispatch/storage/DR plan
│   │   └── curtailment.py                      # baseline vs. optimized curtailment
│   ├── agents/
│   │   ├── orchestrator.py                     # LangGraph StateGraph wiring it all
│   │   └── verifier.py                         # re-checks narrated numbers
│   ├── llm/
│   │   ├── provider.py                         # offline template provider (default)
│   │   └── bob_provider.py                     # IBM Bob/watsonx.ai provider (real, unexercised)
│   ├── api/
│   │   ├── main.py                             # FastAPI app + SSE stream
│   │   ├── run_store.py                        # in-memory run state
│   │   └── schemas.py                          # request models + JSON serializers
│   ├── reports/
│   │   └── pdf_export.py                       # ReportLab one-click PDF brief
│   └── tests/                                  # 42 pytest tests, ~93% coverage
└── frontend/
    └── src/                                     # React 18 + Vite dashboard
```

## Request flow

1. `POST /api/runs` resolves the requested time window against the dataset,
   builds a default `LoadBalanceConfig` from the window's peak load, and
   creates a `RunRecord` in `pending` status. It does not run the pipeline.
2. The frontend opens `GET /api/runs/{id}/stream` (Server-Sent Events).
   That request is what actually executes `stream_pipeline(...)`: a
   LangGraph `.stream()` call that yields after every node
   (`forecast -> anomalies -> load_balance -> curtailment -> narrate ->
   verify`). Each node's `progress_log` lines become SSE `progress` events
   in real time.
3. Once the graph reaches `END`, the accumulated state is serialized
   (`backend/api/schemas.py::serialize_run_result`) and sent as a single SSE
   `result` event, and the run is marked `done` in the store.
4. `GET /api/runs/{id}` lets the frontend re-fetch a completed run without
   re-streaming; `GET /api/runs/{id}/report.pdf` renders the same result
   through `reports/pdf_export.py`.

## Why LangGraph nodes, not one function

Each pipeline stage is a plain Python node function that reads specific
keys off the shared `GridState` TypedDict and returns a partial update --
`progress_log` is the one field with an `operator.add` reducer, so every
node's log lines append rather than overwrite. This keeps each stage
independently testable (see `backend/tests/test_orchestrator.py`, which
runs the whole graph against the real dataset) while still giving the API
layer a clean per-node event to stream.

## Trust boundary

`backend/llm/provider.get_provider()` is the only place a model call could
happen, and only when `NARRATION_PROVIDER=bob` is set with a watsonx API
key -- the default `TemplateNarrationProvider` never leaves the process.
Either way, the provider only ever receives already-computed numbers and
returns prose; `backend/agents/verifier.py` is what actually enforces the
"no fabricated numbers" guarantee, independent of which provider ran.
