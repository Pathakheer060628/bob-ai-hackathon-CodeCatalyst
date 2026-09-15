# GridSentinel — source

- `backend/` — Python/FastAPI/LangGraph pipeline. See `backend/tools/` for
  the deterministic, unit-tested logic (forecasting, anomaly detection,
  root-cause classification, load balancing, curtailment minimization) and
  `backend/agents/` for the LangGraph orchestration + verifier.
- `frontend/` — React 18 + Vite operator dashboard.

Full setup instructions: [`../docs/setup-guide.md`](../docs/setup-guide.md).
