import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createRun, streamRun } from "../api/client.js";
import { useRuns } from "../context/RunContext.jsx";
import RunForm from "../components/RunForm.jsx";
import ProgressFeed from "../components/ProgressFeed.jsx";
import PipelineStepper from "../components/PipelineStepper.jsx";
import Icon from "../components/ui/Icon.jsx";

export default function NewRun() {
  const { datasetInfo, setActiveFromLiveRun, setActiveResultFromLiveRun, setActiveErrorFromLiveRun, refreshRuns } = useRuns();
  const navigate = useNavigate();

  const [runId, setRunId] = useState(null);
  const [progress, setProgress] = useState([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [connection, setConnection] = useState("idle"); // "idle" | "connecting" | "open" | "closed"
  const [completed, setCompleted] = useState(false);

  const seenNodes = useMemo(() => progress.map((p) => p.node), [progress]);

  const handleSubmit = async ({ windowEnd, lookbackDays, horizonHours, loadBalanceConfig, forecastModel }) => {
    setError(null);
    setProgress([]);
    setCompleted(false);
    setRunning(true);
    setConnection("connecting");
    try {
      const { run_id } = await createRun({ windowEnd, lookbackDays, horizonHours, loadBalanceConfig, forecastModel });
      setRunId(run_id);
      setActiveFromLiveRun(run_id);
      streamRun(run_id, {
        onProgress: (data) => setProgress((p) => [...p, data]),
        onResult: (data) => {
          setActiveResultFromLiveRun(data);
          setRunning(false);
          setCompleted(true);
          refreshRuns();
        },
        onError: (message) => {
          setError(message);
          setActiveErrorFromLiveRun(message);
          setRunning(false);
        },
        onConnectionChange: setConnection,
      });
    } catch (e) {
      setError(e.message);
      setRunning(false);
      setConnection("closed");
    }
  };

  return (
    <div>
      <div className="content__heading">
        <h1>New Run / Live Pipeline</h1>
        <p>Configure the analysis window and watch the LangGraph pipeline execute in real time via server-sent events.</p>
      </div>

      {error && (
        <div className="error-banner">
          <Icon name="alertTriangle" size={16} />
          {error}
        </div>
      )}

      <section className="panel panel--control section-gap">
        <div className="section-header">
          <div>
            <div className="section-header__title-row">
              <span className="section-header__icon">
                <Icon name="sliders" size={16} />
              </span>
              <h2>Optimization Controls</h2>
            </div>
            <p className="section-header__subtitle">Choose the "as-of" window; advanced dispatch/storage/demand-response constraints are optional.</p>
          </div>
        </div>
        <RunForm datasetInfo={datasetInfo} onSubmit={handleSubmit} disabled={running} />
      </section>

      {(progress.length > 0 || running) && (
        <section className="card section-gap">
          <div className="section-header">
            <div>
              <div className="section-header__title-row">
                <span className="section-header__icon">
                  <Icon name="activity" size={16} />
                </span>
                <h2>Pipeline Stages</h2>
              </div>
              <p className="section-header__subtitle">
                Only stages that have actually reported a progress event are marked done or active &mdash; no fabricated progress bar.
              </p>
            </div>
            <span className={`status-pill ${connection === "open" ? "status-pill--good" : connection === "connecting" ? "status-pill--active" : connection === "closed" && !completed ? "status-pill--offline" : "status-pill--idle"}`}>
              <span className="status-pill__dot" />
              {connection === "open" ? "Streaming" : connection === "connecting" ? "Connecting" : completed ? "Complete" : "Closed"}
            </span>
          </div>
          <PipelineStepper seenNodes={seenNodes} running={running} />
        </section>
      )}

      {progress.length > 0 && (
        <section className="card section-gap">
          <ProgressFeed entries={progress} running={running} />
        </section>
      )}

      {completed && runId && (
        <section className="panel section-gap" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h2 style={{ margin: "0 0 4px" }}>Run complete</h2>
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>Run {runId} finished. View the results in the detail views.</p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-secondary" onClick={() => navigate("/anomalies")}>
              Anomalies
            </button>
            <button className="btn btn-secondary" onClick={() => navigate("/optimization")}>
              Optimization
            </button>
            <button className="btn btn-primary" onClick={() => navigate("/brief")}>
              Operator Brief
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
