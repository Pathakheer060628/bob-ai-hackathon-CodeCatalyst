# Setup Guide

## Requirements

- Python 3.11+
- Node.js 18+ / npm

Nothing here requires an API key or network access at runtime -- the
default narration provider is fully offline. Network access is only needed
once, to download the raw OPSD dataset if you want to regenerate
`grid_renewable_de_2017_2019.csv` from scratch (it's already committed, so
this is optional -- see `src/backend/data/DATA_SOURCE.md`).

## Backend

```bash
cd src
pip install -e ".[dev]"
python -m pytest backend/tests -q       # 42 passed
uvicorn backend.api.main:app --reload --port 8000
```

Verify it's up:

```bash
curl http://localhost:8000/api/dataset/info
```

## Frontend

```bash
cd src/frontend
npm install
npm run dev
# open http://localhost:5173
```

The Vite dev server proxies `/api/*` to `http://localhost:8000` (see
`vite.config.js`), so the backend must be running first.

## Using it

1. Open the dashboard. It loads the dataset's real date range (2017-01-01
   to 2019-12-31) from `/api/dataset/info`.
2. Pick an "as of" timestamp, a lookback window (how much history to
   analyze for anomalies/seasonality), and a forecast horizon, then click
   **Run Optimisation**.
3. Watch the live agent progress feed (SSE) as each pipeline stage
   completes.
4. Once done: the verifier trust badge, the full operator brief, the
   demand forecast chart (with flagged spikes), the renewable anomaly +
   root-cause table, the load-balancing action plan, and the curtailment
   minimization summary all render. Export the same brief as a PDF from
   the top of the page.

## Enabling the IBM Bob / watsonx.ai narration provider

The default provider is a deterministic offline template. To route
narration through IBM Bob / watsonx.ai instead:

```bash
export NARRATION_PROVIDER=bob
export WATSONX_API_KEY=...
export WATSONX_PROJECT_ID=...
export WATSONX_URL=https://us-south.ml.cloud.ibm.com   # or your region
```

See `src/backend/llm/bob_provider.py` -- the integration code is real and
wired, but wasn't exercised in this build's environment (no network/API
key available).

## Regenerating the dataset (optional)

```bash
cd src/backend/data
curl -L -o time_series_60min.csv \
  https://data.open-power-system-data.org/time_series/2020-10-06/time_series_60min_singleindex.csv
python build_dataset.py
```
