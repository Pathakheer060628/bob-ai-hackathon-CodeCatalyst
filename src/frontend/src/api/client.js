const BASE = "/api";

export async function getDatasetInfo() {
  const res = await fetch(`${BASE}/dataset/info`);
  if (!res.ok) throw new Error(`dataset/info failed: ${res.status}`);
  return res.json();
}

export async function createRun({ windowEnd, lookbackDays, horizonHours }) {
  const res = await fetch(`${BASE}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      window_end: windowEnd,
      lookback_days: lookbackDays,
      horizon_hours: horizonHours,
    }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `create run failed: ${res.status}`);
  }
  return res.json();
}

/**
 * Opens the SSE stream for a run. Calls onProgress(message) for each
 * progress event, onResult(result) once the pipeline completes, and
 * onError(message) if either the pipeline or the connection fails.
 * Returns a cleanup function that closes the EventSource.
 */
export function streamRun(runId, { onProgress, onResult, onError }) {
  const source = new EventSource(`${BASE}/runs/${runId}/stream`);

  source.addEventListener("progress", (event) => {
    const data = JSON.parse(event.data);
    onProgress?.(data);
  });

  source.addEventListener("result", (event) => {
    const data = JSON.parse(event.data);
    onResult?.(data);
    source.close();
  });

  source.addEventListener("error", (event) => {
    if (event.data) {
      try {
        const data = JSON.parse(event.data);
        onError?.(data.message || "Pipeline error");
      } catch {
        onError?.("Connection error");
      }
    } else {
      onError?.("Connection error");
    }
    source.close();
  });

  return () => source.close();
}

export function reportPdfUrl(runId) {
  return `${BASE}/runs/${runId}/report.pdf`;
}
