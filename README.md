# ⚡ GridSentinel

> Grid Load Optimisation & Renewable Energy Performance Advisor
> ---
<img width="1600" height="884" alt="WhatsApp Image 2026-09-16 at 10 50 02 AM" src="https://github.com/user-attachments/assets/f82b9e8e-f7be-4275-89d5-b7f993db2d1d" />

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | CodeCatalyst |
| **Track** | AI Utilities |
| **Team Lead** | Heer Pathak (23ce112@charusat.edu.in) |
| **Members** | Manasvee Viroja (23dcs143@charusat.edu.in), Priyal Kalariya (23dce053@charusat.edu.in), Prince Patel (23ec094@charusat.edu.in) |

---

## 🎯 Problem Statement

The US curtailed ~8 TWh of clean energy in 2023 — renewable electricity
switched off because the grid couldn't absorb it — while unexpected demand
spikes simultaneously threaten grid stability from the other direction.
Operators need to forecast load spikes, balance renewable generation, and
detect underperforming solar/wind assets at the same time, with very
limited real-time decision support today.

See [`docs/problem-statement.md`](docs/problem-statement.md) for the full
writeup.

---

## 💡 Solution

GridSentinel is a single LangGraph pipeline that forecasts demand and flags
spikes, forecasts renewable supply, detects sustained renewable
underperformance via CUSUM change-point detection, classifies a root cause
per anomaly (curtailment-likely / weather-driven / equipment fault /
benign surplus), solves a linear-programming load-balancing plan (dispatch,
battery storage, demand response), and computes a curtailment-minimization
plan by comparing that plan against a no-flexibility baseline. A
deterministic tool computes every number; an LLM only narrates it; a
verifier agent re-checks every number in the generated brief against the
computed state before it's shown to an operator.

See [`docs/solution-overview.md`](docs/solution-overview.md) for the full
writeup.

---

## ✨ Key Features

- **Demand spike forecasting** — seasonal-naive baseline (same weekday/hour
  median over a trailing window) + bounded trend adjustment, flagging hours
  that would be unusual even accounting for the normal weekly pattern
- **CUSUM renewable anomaly detection** per asset class (solar, onshore
  wind, offshore wind) — a real sustained drift gets flagged, not
  single-hour noise
- **Rule-based root-cause classification** — curtailment-likely (oversupply
  vs. load), weather-driven (correlated dip across asset classes),
  equipment/availability fault (isolated to one asset), or benign surplus
- **LP-based load-balancing plan** (scipy `linprog`) — dispatch, battery
  charge/discharge, and demand response solved jointly, hour by hour
- **Curtailment minimization plan** — runs the load-balancing LP twice
  (naive baseline vs. full flexibility) and reports the MWh of clean energy
  the recommended actions actually avoid curtailing
- **Live SSE agent progress feed**, verifier trust badge, and one-click PDF
  export of every run

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python 3.11, JavaScript (React 18) |
| **Frameworks** | FastAPI, LangGraph, Vite |
| **IBM Technologies** | IBM Bob / watsonx.ai (pluggable narration provider — see `src/backend/llm/bob_provider.py`; the default offline template provider is what actually runs in this build, see Known Limitations) |
| **Data / Stats / Optimisation** | pandas, numpy, scipy (`linprog`), PyYAML |
| **Reporting** | Jinja2, ReportLab |
| **Other** | pytest, Server-Sent Events |

---

## 📁 Repository Structure

```
├── src/                  # All source code (backend/ + frontend/)
├── docs/                 # Written documentation
│   ├── plain-language-overview.md   # No-jargon explainer of the whole project
│   ├── PROJECT_OVERVIEW.md          # Technical deep-dive
│   ├── problem-statement.md
│   ├── solution-overview.md
│   ├── architecture.md
│   └── setup-guide.md
├── demo/                 # Demo artifacts
│   ├── screenshots/      # Real, live-browser screenshots of the running app
│   └── demo-video-link.txt
├── presentation/         # Slide deck
└── submission.yaml       # Structured submission metadata
```

---

## ⚡ How to Run

Full details in [`docs/setup-guide.md`](docs/setup-guide.md). Short version:

```bash
# Backend
cd src
pip install -e ".[dev]"
python -m pytest backend/tests -q        # 42 passed
uvicorn backend.api.main:app --reload --port 8000

# Frontend (separate terminal)
cd src/frontend
npm install
npm run dev
# open http://localhost:5173
```

Nothing above requires an API key or network access — the default
narration provider runs fully offline, and the real dataset is already
committed to the repo.

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo | [See demo/live-demo-url.txt](demo/live-demo-url.txt) |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) — captured from the actual running app in a live browser |
| 📊 Presentation | [See presentation/](presentation/) |

---

## ⚠️ Known Limitations

- **The demonstrated dataset is real, not synthetic** — a genuine hourly
  extract of German grid load, solar, and wind generation (2017-2019) from
  Open Power System Data / ENTSO-E — but it's one country over one
  three-year window. See `src/backend/data/DATA_SOURCE.md` for full
  provenance and how to point the system at a different extract.
- **Curtailment is legitimately near-zero in most windows of this
  particular dataset** — at the German national aggregate scale in
  2017-2019, renewable output rarely exceeded total demand simultaneously
  (real national curtailment was a small, largely regional phenomenon in
  this period). The curtailment-minimization LP is verified correct against
  synthetic oversupply scenarios in `backend/tests/test_curtailment.py` and
  will report nonzero avoided curtailment automatically on any window (or
  future dataset) where renewable forecast approaches or exceeds demand —
  which is increasingly the case on grids with higher renewable
  penetration, exactly the situation this challenge describes.
- **The IBM Bob/watsonx.ai narration provider (`llm/bob_provider.py`) is
  real, wired code but was not exercised** — this build environment has no
  watsonx API key. The default template provider (fully offline,
  deterministic) is what the demo actually runs on, and produces the same
  facts, just via string templates instead of a model call.
- **Run storage is in-memory** (`backend/api/run_store.py`) — correct for
  this demo, would need a real database for multi-user or persistent use.
- **The frontend's load-balancing configuration (storage size, dispatch
  capacity, demand-response ceiling) is a sensible default computed from
  each window's peak load, not yet exposed as a UI control** — the API
  already accepts overrides (`backend/api/schemas.py::LoadBalanceConfigIn`).

---

## 🏅 What We're Most Proud Of

The **verifier agent** (`src/backend/agents/verifier.py`): after the
narrator drafts a brief, the verifier independently re-extracts every
number that appears in the prose and checks it against the actual computed
statistics in the pipeline state, flagging anything that doesn't trace
back. Paired with the "LLM narrates, never calculates" rule enforced
throughout the backend (every forecast, anomaly, load-balancing, and
curtailment number comes from a typed, independently unit-tested tool —
never a model call), this is what makes it defensible to hand this tool's
output to a grid operator making real dispatch decisions.
`backend/tests/test_verifier.py` includes a test that simulates a narrator
fabricating a number and confirms the verifier catches it.
