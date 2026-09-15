# Solution Overview

GridSentinel is a single LangGraph pipeline over real grid data:

```
forecast demand + renewables
        |
detect renewable anomalies (CUSUM, per asset class)
        |
classify root cause (curtailment / weather / equipment / benign)
        |
solve load-balancing LP (dispatch, storage, demand response)
        |
compute curtailment-minimization plan (baseline vs. optimized)
        |
narrate -> verify
```

Every number in the final brief is computed by a typed, independently
unit-tested tool -- an LLM (or the offline template provider that runs by
default) only phrases those numbers into prose. A verifier agent
re-extracts every figure from the generated text and checks it against the
computed state before the brief is considered trustworthy; a fabricated
number fails verification and is flagged, never silently shipped.

## The five capabilities, and where they live

| Challenge requirement | Implementation |
|---|---|
| Forecast demand spikes | `backend/tools/forecasting.py::forecast_demand` -- seasonal-naive baseline (median load for the same weekday/hour over a trailing window) + a bounded recent-trend adjustment; a spike is an hour that would be unusual even accounting for the normal weekly pattern |
| Recommend load-balancing actions | `backend/tools/load_balancing.py::solve_load_balance` -- a linear program (scipy `linprog`) choosing dispatch, battery charge/discharge, and demand response per hour to meet forecast demand at minimum cost |
| Detect renewable performance anomalies | `backend/tools/anomaly_detection.py::detect_renewable_anomalies` -- CUSUM change-point detection over (actual - expected) capacity factor per asset class, so a real sustained drift is flagged, not single-hour noise |
| Identify root cause per underperforming asset | `backend/tools/root_cause.py::classify_root_cause` -- rule-based classification (curtailment-likely vs. weather-driven vs. equipment fault vs. benign surplus) from the renewable-to-load ratio and cross-asset correlation |
| Integrated brief + curtailment minimisation plan | `backend/tools/curtailment.py::minimize_curtailment` runs the load-balancing LP twice (a no-flexibility baseline vs. the fully configured plan) and reports the MWh difference as avoided curtailment; `backend/agents/orchestrator.py` wires everything into one run, and `backend/llm/provider.py` + `backend/agents/verifier.py` produce and check the brief |

## Why a real dataset, not synthetic

The backend runs on a real, historical, hourly extract of German grid load
and solar/wind generation (2017-2019), sourced from the Open Power System
Data project (itself built from ENTSO-E Transparency Platform TSO reports).
Genuine demand spikes, genuine multi-day wind lulls and surges, and genuine
forecast-vs-actual gaps are all present -- see
`src/backend/data/DATA_SOURCE.md` for the full provenance and how to
regenerate it.

## What we're most proud of

The **verifier agent** (`backend/agents/verifier.py`). It independently
re-extracts every number from the generated brief and checks it traces back
to a real computed statistic within a small rounding tolerance -- catching,
for example, a narrator that invents a plausible-sounding but fabricated
total. `backend/tests/test_verifier.py` includes a test that injects a
fabricated number into a real brief and confirms the verifier flags it.
Combined with the rule enforced everywhere in this backend -- a model
*narrates*, it never *calculates* -- this is what makes it defensible to
hand GridSentinel's output to a grid operator making real dispatch
decisions.
