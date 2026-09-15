import { useEffect, useMemo, useRef, useState } from "react";
import { createRun, getDatasetInfo, reportPdfUrl, streamRun } from "./api/client.js";
import RunForm from "./components/RunForm.jsx";
import ProgressFeed from "./components/ProgressFeed.jsx";
import DemandForecastChart from "./components/DemandForecastChart.jsx";
import AnomalyPanel from "./components/AnomalyPanel.jsx";
import LoadBalancePanel from "./components/LoadBalancePanel.jsx";
import CurtailmentPanel from "./components/CurtailmentPanel.jsx";
import VerifierBadge from "./components/VerifierBadge.jsx";
import NarrativeBrief from "./components/NarrativeBrief.jsx";
import Header from "./components/ui/Header.jsx";
import Sidebar from "./components/ui/Sidebar.jsx";
import StatCard from "./components/ui/StatCard.jsx";
import Icon from "./components/ui/Icon.jsx";

export default function App() {
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [runId, setRunId] = useState(null);
  const [progress, setProgress] = useState([]);
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeId, setActiveId] = useState("section-overview");

  const contentRef = useRef(null);

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

  // Scroll-spy: highlights the sidebar item whose section is currently in
  // view. Purely visual — reads the DOM sections that already exist, adds
  // no state that other components consume.
  useEffect(() => {
    const ids = [
      "section-overview",
      "section-optimization",
      "section-forecast",
      "section-anomalies",
      "section-loadbalance",
      "section-curtailment",
      "section-verification",
      "section-brief",
    ];
    const els = ids.map((id) => document.getElementById(id)).filter(Boolean);
    if (!els.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActiveId(visible[0].target.id);
      },
      { root: null, rootMargin: "-96px 0px -70% 0px", threshold: 0 }
    );
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [result]);

  const availableIds = useMemo(() => {
    const ids = new Set(["section-optimization"]);
    if (progress.length > 0) ids.add("section-progress");
    if (result) {
      ids.add("section-overview");
      ids.add("section-forecast");
      ids.add("section-anomalies");
      ids.add("section-loadbalance");
      ids.add("section-curtailment");
      ids.add("section-verification");
      ids.add("section-brief");
    }
    return ids;
  }, [progress.length, result]);

  const kpis = useMemo(() => {
    if (!result) return null;
    const peak = result.forecast?.peak;
    const plan = result.load_balance;
    const curtailment = result.curtailment;
    const verification = result.verification;
    return {
      peakMw: peak ? peak.forecast_mw : null,
      cost: plan?.feasible ? plan.total_cost : null,
      curtailedMwh: curtailment ? curtailment.optimized_curtailed_mwh : null,
      unmetMwh: plan?.feasible ? plan.total_unmet_mwh : null,
      verifiedCount: verification ? verification.checked_count : null,
    };
  }, [result]);

  return (
    <div className="shell">
      <Sidebar availableIds={availableIds} activeId={activeId} open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />
      {sidebarOpen && <div className="sidebar__backdrop sidebar__backdrop--visible" onClick={() => setSidebarOpen(false)} />}

      <div className="shell__main">
        <Header
          datasetInfo={datasetInfo}
          running={running}
          verified={result ? result.verification?.trusted : null}
          onMenuClick={() => setSidebarOpen((o) => !o)}
        />

        <main className="content" ref={contentRef}>
          <div className="content__heading">
            <h1>Grid Operations Dashboard</h1>
            <p>Forecast, optimization and renewable performance overview</p>
          </div>

          {error && (
            <div className="error-banner">
              <Icon name="alertTriangle" size={16} />
              {error}
            </div>
          )}

          <section id="section-optimization" className="panel panel--control section-gap">
            <SectionTitle icon="sliders" title="Optimization Controls" subtitle="Configure the analysis window and run the pipeline" />
            <RunForm datasetInfo={datasetInfo} onSubmit={handleSubmit} disabled={running} />
          </section>

          {progress.length > 0 && (
            <section id="section-progress" className="card section-gap">
              <ProgressFeed entries={progress} running={running} />
            </section>
          )}

          {result && (
            <>
              <section id="section-overview" className="kpi-grid section-gap">
                <StatCard label="Forecast Peak" value={fmt(kpis.peakMw, 0)} unit="MW" icon="trendingUp" tone="neutral" />
                <StatCard
                  label="Est. Operating Cost"
                  value={kpis.cost != null ? `$${fmt(kpis.cost, 0)}` : "N/A"}
                  icon="dollar"
                  tone="neutral"
                />
                <StatCard label="Curtailment" value={fmt(kpis.curtailedMwh, 1)} unit="MWh" icon="scissors" tone="good" />
                <StatCard
                  label="Unmet Load"
                  value={kpis.unmetMwh != null ? fmt(kpis.unmetMwh, 1) : "N/A"}
                  unit={kpis.unmetMwh != null ? "MWh" : ""}
                  icon="alertTriangle"
                  tone={kpis.unmetMwh == null ? "warning" : kpis.unmetMwh > 0 ? "critical" : "good"}
                />
              </section>

              <section id="section-verification" className="panel section-gap">
                <div className="verify-panel">
                  <VerifierBadge verification={result.verification} />
                  <div className="export-bar">
                    <a href={reportPdfUrl(runId)} target="_blank" rel="noreferrer">
                      <span className="btn btn-secondary">
                        <Icon name="download" size={15} />
                        Export PDF brief
                      </span>
                    </a>
                  </div>
                </div>
              </section>

              <section id="section-brief" className="section-gap">
                <NarrativeBrief narrative={result.narrative} provider={result.narration_provider} />
              </section>

              <section id="section-forecast" className="card section-gap">
                <SectionTitle icon="trendingUp" title="Demand Forecast" subtitle="24-hour forecast horizon" />
                <DemandForecastChart forecast={result.forecast} />
              </section>

              <section id="section-anomalies" className="section-gap">
                <AnomalyPanel anomalies={result.anomalies} />
              </section>

              <section id="section-loadbalance" className="section-gap">
                <LoadBalancePanel plan={result.load_balance} />
              </section>

              <section id="section-curtailment" className="section-gap">
                <CurtailmentPanel curtailment={result.curtailment} />
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function SectionTitle({ icon, title, subtitle }) {
  return (
    <div className="section-header">
      <div>
        <div className="section-header__title-row">
          <span className="section-header__icon">
            <Icon name={icon} size={16} />
          </span>
          <h2>{title}</h2>
        </div>
        {subtitle && <p className="section-header__subtitle">{subtitle}</p>}
      </div>
    </div>
  );
}

function fmt(value, digits) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
