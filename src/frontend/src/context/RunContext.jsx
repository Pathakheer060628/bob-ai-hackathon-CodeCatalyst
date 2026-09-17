import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { getDatasetInfo, getRun, listRuns, pingBackend } from "../api/client.js";

const RunContext = createContext(null);

/**
 * App-wide state that every routed page needs: dataset bounds, backend
 * connectivity, the recent-runs list, and the "active run" a viewer is
 * currently looking at (either the run just streamed live on the New Run
 * page, or one loaded read-only from Run History). Pages read from here
 * instead of re-fetching/re-deriving the same state independently.
 */
export function RunProvider({ children }) {
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [backendStatus, setBackendStatus] = useState("checking"); // "checking" | "online" | "offline"
  const [runs, setRuns] = useState([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [activeRunId, setActiveRunId] = useState(null);
  const [activeResult, setActiveResult] = useState(null);
  const [activeStatus, setActiveStatus] = useState(null); // "pending" | "running" | "done" | "error"
  const [activeError, setActiveError] = useState(null);

  const pollRef = useRef(null);

  const refreshRuns = useCallback(async () => {
    setRunsLoading(true);
    try {
      const list = await listRuns(25);
      setRuns(list);
      setBackendStatus("online");
    } catch {
      setBackendStatus("offline");
    } finally {
      setRunsLoading(false);
    }
  }, []);

  useEffect(() => {
    getDatasetInfo()
      .then((info) => {
        setDatasetInfo(info);
        setBackendStatus("online");
      })
      .catch(() => setBackendStatus("offline"));
    refreshRuns();

    // Periodic connectivity probe so the top bar reflects a backend that
    // goes down or comes back up while the app is open.
    pollRef.current = setInterval(async () => {
      const ok = await pingBackend();
      setBackendStatus(ok ? "online" : "offline");
    }, 15000);
    return () => clearInterval(pollRef.current);
  }, [refreshRuns]);

  /** Called by the New Run page as the live SSE pipeline progresses/completes. */
  const setActiveFromLiveRun = useCallback((runId) => {
    setActiveRunId(runId);
    setActiveResult(null);
    setActiveStatus("running");
    setActiveError(null);
  }, []);

  const setActiveResultFromLiveRun = useCallback((result) => {
    setActiveResult(result);
    setActiveStatus("done");
  }, []);

  const setActiveErrorFromLiveRun = useCallback((message) => {
    setActiveError(message);
    setActiveStatus("error");
  }, []);

  /** Called by Run History / a direct /runs/:id visit — loads a past run read-only. */
  const loadRunById = useCallback(async (runId) => {
    setActiveRunId(runId);
    setActiveStatus("pending");
    setActiveError(null);
    try {
      const record = await getRun(runId);
      setActiveStatus(record.status);
      setActiveResult(record.result || null);
      setActiveError(record.error || null);
      return record;
    } catch (e) {
      setActiveStatus("error");
      setActiveError(e.message);
      return null;
    }
  }, []);

  const value = {
    datasetInfo,
    backendStatus,
    runs,
    runsLoading,
    refreshRuns,
    activeRunId,
    activeResult,
    activeStatus,
    activeError,
    setActiveFromLiveRun,
    setActiveResultFromLiveRun,
    setActiveErrorFromLiveRun,
    loadRunById,
  };

  return <RunContext.Provider value={value}>{children}</RunContext.Provider>;
}

export function useRuns() {
  const ctx = useContext(RunContext);
  if (!ctx) throw new Error("useRuns must be used within a RunProvider");
  return ctx;
}
