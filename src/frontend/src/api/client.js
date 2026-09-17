const BASE = "/api";

export async function getDatasetInfo() {
  const res = await fetch(`${BASE}/dataset/info`);
  if (!res.ok) throw new Error(`dataset/info failed: ${res.status}`);
  return res.json();
}

export async function createRun({ windowEnd, lookbackDays, horizonHours, loadBalanceConfig }) {
  const res = await fetch(`${BASE}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      window_end: windowEnd,
      lookback_days: lookbackDays,
      horizon_hours: horizonHours,
      load_balance_config: loadBalanceConfig || undefined,
    }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `create run failed: ${res.status}`);
  }
  return res.json();
}

/** GET /api/runs — recent run summaries, newest first. */
export async function listRuns(limit = 25) {
  const res = await fetch(`${BASE}/runs?limit=${limit}`);
  if (!res.ok) throw new Error(`list runs failed: ${res.status}`);
  const body = await res.json();
  return body.runs || [];
}

/** GET /api/runs/{id} — full status/result for a single run, no re-run. */
export async function getRun(runId) {
  const res = await fetch(`${BASE}/runs/${runId}`);
  if (!res.ok) throw new Error(`get run failed: ${res.status}`);
  return res.json();
}

/**
 * Opens the SSE stream for a run. Calls onProgress(message) for each
 * progress event, onResult(result) once the pipeline completes,
 * onError(message) if the pipeline itself fails, and onConnectionChange
 * (status: "connecting" | "open" | "closed") so the UI can reflect real
 * SSE connectivity instead of assuming it's always live.
 *
 * EventSource retries transport-level drops on its own; we surface that as
 * a bounded number of "connecting" -> "open" cycles rather than silently
 * hanging, and give up (closing cleanly) after a few consecutive failures
 * so the UI can tell the user to retry instead of spinning forever.
 */
export function streamRun(runId, { onProgress, onResult, onError, onConnectionChange }) {
  const source = new EventSource(`${BASE}/runs/${runId}/stream`);
  let settled = false;
  let failureCount = 0;
  const MAX_CONSECUTIVE_FAILURES = 4;

  onConnectionChange?.("connecting");

  source.addEventListener("open", () => {
    failureCount = 0;
    onConnectionChange?.("open");
  });

  source.addEventListener("progress", (event) => {
    const data = JSON.parse(event.data);
    onProgress?.(data);
  });

  source.addEventListener("result", (event) => {
    const data = JSON.parse(event.data);
    settled = true;
    onResult?.(data);
    onConnectionChange?.("closed");
    source.close();
  });

  source.addEventListener("error", (event) => {
    if (settled) return;
    if (event.data) {
      // A structured "error" event from the backend (pipeline failure) --
      // this is terminal, the server already closed the stream.
      try {
        const data = JSON.parse(event.data);
        onError?.(data.message || "Pipeline error");
      } catch {
        onError?.("Pipeline error");
      }
      settled = true;
      onConnectionChange?.("closed");
      source.close();
      return;
    }

    // A raw transport-level drop. The browser's EventSource will attempt
    // to reconnect automatically; we just track and surface that.
    failureCount += 1;
    onConnectionChange?.("connecting");
    if (failureCount >= MAX_CONSECUTIVE_FAILURES) {
      onError?.("Lost connection to the backend and could not reconnect.");
      onConnectionChange?.("closed");
      source.close();
    }
  });

  return () => {
    settled = true;
    source.close();
  };
}

export function reportPdfUrl(runId) {
  return `${BASE}/runs/${runId}/report.pdf`;
}

/** Lightweight backend reachability probe for the top-bar connectivity pill. */
export async function pingBackend() {
  try {
    const res = await fetch(`${BASE}/dataset/info`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}
