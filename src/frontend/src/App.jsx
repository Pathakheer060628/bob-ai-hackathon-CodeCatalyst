import { useEffect, useState } from "react";
import { createRun, getDatasetInfo, reportPdfUrl, streamRun } from "./api/client.js";
import RunForm from "./components/RunForm.jsx";
import ProgressFeed from "./components/ProgressFeed.jsx";
import DemandForecastChart from "./components/DemandForecastChart.jsx";
import AnomalyPanel from "./components/AnomalyPanel.jsx";
import LoadBalancePanel from "./components/LoadBalancePanel.jsx";
import CurtailmentPanel from "./components/CurtailmentPanel.jsx";
import VerifierBadge from "./components/VerifierBadge.jsx";
import NarrativeBrief from "./components/NarrativeBrief.jsx";

export default function App() {
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [runId, setRunId] = useState(null);
  const [progress, setProgress] = useState([]);
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDatasetInfo().then(setDatasetInfo).catch((e) => setError(e.message));
  }, []);

  const handleSubmit = async ({ windowEnd, lookbackDays, horizonHours }) => {
    setError(null);
    setResult(null);
    setProgress([]);
    setRunning(true);
    try {
      const { run_id } = await createRun({ windowEnd, lookbackDays, horizonHours });
      setRunId(run_id);
      streamRun(run_id, {
        onProgress: (data) => setProgress((p) => [...p, data]),
        onResult: (data) => {
          setResult(data);
          setRunning(false);
        },
        onError: (message) => {
          setError(message);
          setRunning(false);
        },
      });
    } catch (e) {
      setError(e.message);
      setRunning(false);
    }
  };

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <h1 className="app__title">GridSentinel</h1>
          <p className="app__subtitle">Grid load optimisation &amp; renewable curtailment minimisation</p>
        </div>
        {datasetInfo && (
          <p className="app__subtitle">
            Real dataset: {datasetInfo.source} ({datasetInfo.license})
          </p>
        )}
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <h2>Run Optimisation</h2>
        <RunForm datasetInfo={datasetInfo} onSubmit={handleSubmit} disabled={running} />
      </div>

      {progress.length > 0 && (
        <div className="card">
          <ProgressFeed entries={progress} />
        </div>
      )}

      {result && (
        <>
          <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
            <VerifierBadge verification={result.verification} />
            <div className="export-bar">
              <a href={reportPdfUrl(runId)} target="_blank" rel="noreferrer">
                Export PDF brief ↓
              </a>
            </div>
          </div>

          <NarrativeBrief narrative={result.narrative} provider={result.narration_provider} />

          <div className="card">
            <h2>Demand Forecast</h2>
            <DemandForecastChart forecast={result.forecast} />
          </div>

          <AnomalyPanel anomalies={result.anomalies} />
          <LoadBalancePanel plan={result.load_balance} />
          <CurtailmentPanel curtailment={result.curtailment} />
        </>
      )}
    </div>
  );
}
