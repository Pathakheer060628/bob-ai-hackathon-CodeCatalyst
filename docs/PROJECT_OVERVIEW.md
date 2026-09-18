# GridSentinel — Project Overview

One consolidated reference for understanding the whole project: what it does, what it's
built with, how the pieces fit together, and how it was developed end-to-end. This
document summarizes and links out to the more detailed files already in `docs/`.

---

## 1. What GridSentinel Is

GridSentinel is a **grid load optimisation and renewable energy performance advisor**.
It's a single automated pipeline that takes real historical grid data and, for any
chosen time window, produces a verified, human-readable operator brief covering:

- where demand is heading and whether it's about to spike,
- which renewable assets (solar, onshore wind, offshore wind) are underperforming and why,
- what to do about it hour-by-hour (dispatch, battery storage, demand response), and
- how much clean energy curtailment those actions actually avoid.

**Problem it solves:** grid operators today do this forecasting / anomaly-detection /
root-causing / optimisation work manually, with fragmented tooling, under time
pressure — while ~8 TWh of clean energy was curtailed in the US in 2023 simply because
the grid couldn't absorb it fast enough. See `docs/problem-statement.md`.

---

## 2. Core Functionality

| Capability | What it does | Implemented in |
|---|---|---|
| **Demand forecasting & spike detection** | Seasonal-naive baseline (median load for same weekday/hour over a trailing window) + a bounded recent-trend adjustment; flags hours that would be unusual even accounting for the normal weekly pattern | `backend/tools/forecasting.py` |
| **Renewable supply forecasting** | Same seasonal-naive approach applied to solar/wind output | `backend/tools/forecasting.py` |
| **Renewable anomaly detection** | CUSUM (cumulative sum) change-point detection on (actual − expected) capacity factor, per asset class — catches a real sustained drift, ignores single-hour noise | `backend/tools/anomaly_detection.py` |
| **Root-cause classification** | Rule-based: curtailment-likely (oversupply vs. load), weather-driven (correlated dip across asset classes), equipment/availability fault (isolated to one asset), or benign/favorable surplus | `backend/tools/root_cause.py` |
| **Load-balancing plan** | Linear program (scipy `linprog`) solving dispatch, battery charge/discharge, and demand response jointly, hour by hour, to meet demand at minimum cost | `backend/tools/load_balancing.py` |
| **Curtailment minimization** | Runs the load-balancing LP twice — a no-flexibility baseline vs. the fully configured plan — and reports the MWh of clean energy actually saved from curtailment | `backend/tools/curtailment.py` |
| **Narration** | Turns the computed numbers into a readable operator brief. Default is a deterministic offline template; can be swapped for an IBM Bob/watsonx.ai LLM call | `backend/llm/provider.py`, `backend/llm/bob_provider.py` |
| **Verification** | Independently re-extracts every number that appears in the narrated brief and checks it against the actual computed state before it's shown to an operator — catches any fabricated or hallucinated figure | `backend/agents/verifier.py` |
| **Orchestration** | Wires all of the above into one LangGraph pipeline, streamed node-by-node | `backend/agents/orchestrator.py` |
| **API + live progress** | REST endpoints to start a run, stream its progress via Server-Sent Events, fetch the finished result, and export it as PDF | `backend/api/main.py` |
| **Dashboard** | React UI: run configuration form, live progress feed, verifier trust badge, demand chart, anomaly/root-cause table, load-balancing plan, curtailment summary, one-click PDF export | `frontend/src/` |

**Design principle enforced everywhere:** a deterministic, independently unit-tested
tool computes every number. The LLM (or the offline template provider used by default)
only *narrates* those numbers into prose — it never calculates anything. The verifier
agent is the safety net that catches it if that rule is ever violated.

---

## 3. Technology Stack

| Layer | Technology |
|---|---|
| Backend language | Python 3.11 |
| Backend API framework | FastAPI (+ Server-Sent Events for live progress) |
| Agent orchestration | LangGraph (`StateGraph`) |
| Data / numerics | pandas, numpy |
| Optimisation | scipy (`linprog` — linear programming) |
| Config / serialization | PyYAML, Pydantic (via FastAPI schemas) |
| Reporting | Jinja2 (templating) + ReportLab (PDF generation) |
| LLM narration (optional) | IBM Bob / watsonx.ai — pluggable provider, real but not exercised in this build (no API key in the dev environment); default provider is a fully offline template |
| Testing | pytest, pytest-cov |
| Frontend language | JavaScript |
| Frontend framework | React 18 |
| Frontend build tool | Vite (dev server proxies `/api/*` to the FastAPI backend) |
| Data source | Real hourly German grid load + solar/wind generation, 2017–2019, from Open Power System Data (built from ENTSO-E Transparency Platform TSO reports) |

No API key or network access is required to run the project — the default narration
provider runs entirely offline and the dataset is already committed to the repo.

---

## 4. Architecture & Request Flow

```
src/
├── backend/
│   ├── data/        dataset CSV + loader (cached DataFrame) + regeneration script
│   ├── tools/        deterministic, typed, unit-tested calculators
│   │                 (forecasting, anomaly_detection, root_cause,
│   │                  load_balancing, curtailment)
│   ├── agents/        orchestrator.py (LangGraph StateGraph wiring),
│   │                 verifier.py (re-checks narrated numbers)
│   ├── llm/          provider.py (offline template, default),
│   │                 bob_provider.py (IBM Bob/watsonx.ai, optional)
│   ├── api/          main.py (FastAPI app + SSE stream), run_store.py
│   │                 (in-memory run state), schemas.py (request/response models)
│   ├── reports/      pdf_export.py (ReportLab PDF brief)
│   └── tests/        pytest suite (50 tests, ~94% coverage)
└── frontend/
    └── src/          React 18 + Vite dashboard
```

**End-to-end request flow (one "run"):**

1. `POST /api/runs` — the frontend submits a time window (as-of timestamp, lookback,
   forecast horizon). The backend resolves it against the dataset, builds a default
   load-balancing config from that window's peak load, and creates a `RunRecord` in
   `pending` status. The pipeline has **not** executed yet.
2. The frontend opens `GET /api/runs/{id}/stream` (Server-Sent Events). This request is
   what actually triggers `stream_pipeline(...)` — a LangGraph `.stream()` call that
   yields after each node:
   `forecast → anomalies → load_balance → curtailment → narrate → verify`.
   Each node's log lines are pushed to the frontend as SSE `progress` events in real
   time, which is what powers the live progress feed in the UI.
3. When the graph reaches `END`, the full accumulated state is serialized
   (`schemas.py::serialize_run_result`) and sent as one SSE `result` event; the run is
   marked `done`.
4. `GET /api/runs/{id}` lets the frontend re-fetch a completed run without
   re-streaming. `GET /api/runs/{id}/report.pdf` renders the same result through
   `reports/pdf_export.py`.

**Why LangGraph nodes instead of one function:** each stage is a plain Python function
reading/writing a shared `GridState` TypedDict. `progress_log` uses an `operator.add`
reducer so every node's log lines append rather than overwrite. This keeps every stage
independently unit-testable while still giving the API a clean per-node event to stream.

**Trust boundary:** `backend/llm/provider.get_provider()` is the *only* place a model
call could ever happen, and only if `NARRATION_PROVIDER=bob` is explicitly set with a
watsonx API key — otherwise the default `TemplateNarrationProvider` never leaves the
process. Either way, the provider only ever receives already-computed numbers and
returns prose. `backend/agents/verifier.py` is what actually enforces the
"no fabricated numbers" guarantee, independent of which narration provider ran.

Full detail: `docs/architecture.md`.

---

## 5. End-to-End Development Process

This is how the project was actually built, in sequence:

1. **Problem framing** — started from the hackathon's "Grid Load Optimisation &
   Renewable Energy" challenge statement; wrote it up in `docs/problem-statement.md`
   to pin down exactly what an operator needs (forecast, watch, decide, brief).
2. **Data sourcing** — chose a real dataset over a synthetic one for credibility:
   hourly German grid load + solar/wind generation (2017–2019) from Open Power System
   Data / ENTSO-E. `backend/data/build_dataset.py` regenerates the committed CSV from
   the raw OPSD source if needed; `backend/data/loader.py` provides a cached,
   validated DataFrame with derived columns. Provenance documented in
   `backend/data/DATA_SOURCE.md`.
3. **Deterministic tools first** — built and unit-tested each calculation in isolation
   before any orchestration or UI existed: forecasting → anomaly detection → root
   cause → load balancing → curtailment. Each tool is a typed, pure function with its
   own pytest module.
4. **Orchestration** — wired the five tools into a single LangGraph `StateGraph`
   (`agents/orchestrator.py`) with a shared state object, so the pipeline runs as one
   sequential graph and can be streamed node-by-node.
5. **Narration + verification layer** — added an LLM-narration step (pluggable:
   offline template by default, IBM Bob/watsonx.ai optionally) that only phrases
   already-computed numbers into prose, followed by a verifier agent
   (`agents/verifier.py`) that independently re-extracts every number from that prose
   and checks it against the real computed state, flagging anything that doesn't
   trace back — including a test that deliberately injects a fabricated number to
   confirm the verifier catches it.
6. **API layer** — exposed the pipeline over FastAPI: run creation, an SSE endpoint
   that actually executes and streams the pipeline live, run retrieval, and PDF export.
7. **Frontend** — built the React 18 + Vite dashboard: run configuration form, live
   SSE progress feed, verifier trust badge, demand forecast chart, anomaly/root-cause
   table, load-balancing panel, curtailment summary, and one-click PDF export.
8. **Testing & QA** — grew the pytest suite to 50 tests across 9 categories (dataset,
   forecasting, anomaly detection, root cause, load balancing, curtailment, verifier/
   narration, orchestrator, API/SSE/report), reaching 94% statement coverage; full
   results in `TEST_REPORT.md`.
9. **Documentation & packaging** — wrote `docs/architecture.md`,
   `docs/solution-overview.md`, `docs/setup-guide.md`, recorded demo screenshots and
   video (`demo/`), built the presentation deck (`presentation/`), and filled in
   `submission.yaml` for the hackathon submission pipeline.

---

## 6. Running It Locally

```bash
# Backend
cd src
pip install -e ".[dev]"
python -m pytest backend/tests -q        # 50 passed
uvicorn backend.api.main:app --reload --port 8000

# Frontend (separate terminal)
cd src/frontend
npm install
npm run dev
# open http://localhost:5173
```

No API key or network access needed — the default narration provider is fully
offline and the dataset is already committed. To route narration through IBM
Bob/watsonx.ai instead, set `NARRATION_PROVIDER=bob` plus the relevant
`WATSONX_*` environment variables (see `docs/setup-guide.md`).

**Using the dashboard:** open it, pick an "as of" timestamp, a lookback window, and a
forecast horizon, click **Run Optimisation**, watch the live progress feed, then read
the verifier badge, operator brief, demand chart, anomaly/root-cause table,
load-balancing plan, and curtailment summary — or export the whole thing as a PDF.

---

## 7. Testing & Quality

- **50/50 tests passing**, 94% statement coverage (1,314 statements, 79 missed), full
  suite runs in ~5.6s.
- Categories: Dataset & Loader (7), Forecasting (7), Anomaly Detection (7), Root Cause
  (5), Load Balancing (7), Curtailment (4), Verifier & Narration (5), Orchestrator (3),
  API/SSE/Report (5).
- Two intentionally uncovered modules, both honestly disclosed rather than hidden:
  `llm/bob_provider.py` (0% — no watsonx credentials in this environment, and the task
  rules disallow a real network call in normal tests) and `data/build_dataset.py` (0%
  — a one-off offline script not on the runtime request path).
- Full detail: `TEST_REPORT.md`.

---

## 8. Known Limitations

- The dataset is real but limited to one country (Germany) and one three-year window
  (2017–2019).
- Curtailment is legitimately near-zero in most windows of this specific dataset,
  since German national renewable output rarely exceeded demand in this period. The
  curtailment-minimization LP is independently verified correct against synthetic
  oversupply scenarios (`backend/tests/test_curtailment.py`) and will report nonzero
  avoided curtailment automatically on any window (or future dataset) where renewable
  forecast approaches or exceeds demand.
- `llm/bob_provider.py` (IBM Bob/watsonx.ai) is real, wired code but wasn't exercised
  in this build — no watsonx API key was available in the environment. The default
  offline template provider is what actually runs the demo, producing the same facts
  via string templates instead of a model call.
- Run storage is in-memory (`backend/api/run_store.py`) — fine for a demo, would need
  a real database for multi-user or persistent use.
- Load-balancing configuration (storage size, dispatch capacity, demand-response
  ceiling) defaults sensibly from each window's peak load but isn't yet exposed as a
  UI control, even though the API already accepts overrides.

---

## 9. What the Team Is Most Proud Of

The **verifier agent** (`backend/agents/verifier.py`): after the narrator drafts a
brief, the verifier independently re-extracts every number that appears in the prose
and checks it against the actual computed statistics in the pipeline state, flagging
anything that doesn't trace back. Combined with the "LLM narrates, never calculates"
rule enforced throughout the backend, this is what makes it defensible to hand
GridSentinel's output to a grid operator making real dispatch decisions.
`backend/tests/test_verifier.py` includes a test that simulates a narrator fabricating
a number and confirms the verifier catches it.

---

## 10. Team

| Field | Value |
|---|---|
| Team Name | CodeCatalyst |
| Track | AI Utilities |
| Team Lead | Heer Pathak (23ce112@charusat.edu.in) |
| Members | Manasvee Viroja (23dcs143@charusat.edu.in), Priyal Kalariya (23dce053@charusat.edu.in), Prince Patel (23ec094@charusat.edu.in) |

---

## 11. Reference Documents

- `docs/plain-language-overview.md` — the no-jargon version of this document
- `docs/problem-statement.md` — full problem writeup
- `docs/solution-overview.md` — solution summary and challenge-requirement mapping
- `docs/architecture.md` — component and request-flow detail
- `docs/setup-guide.md` — full local setup instructions
- `TEST_REPORT.md` — full test execution and coverage report
- `src/backend/data/DATA_SOURCE.md` — dataset provenance
- `submission.yaml` — structured hackathon submission metadata
