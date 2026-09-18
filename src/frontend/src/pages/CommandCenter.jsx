import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getRun } from "../api/client.js";
import { useRuns } from "../context/RunContext.jsx";
import StatCard from "../components/ui/StatCard.jsx";
import Icon from "../components/ui/Icon.jsx";
import DemandForecastChart from "../components/DemandForecastChart.jsx";
import EmptyRunState from "../components/ui/EmptyRunState.jsx";

function fmt(value, digits = 0) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export default function CommandCenter() {
  const { runs, runsLoading, backendStatus, refreshRuns } = useRuns();
  const [latestResult, setLatestResult] = useState(null);
  const [latestLoading, setLatestLoading] = useState(false);

  const latestDone = useMemo(() => runs.find((r) => r.status === "done") || null, [runs]);
  const latestAny = runs[0] || null;

  useEffect(() => {
    if (!latestDone) {
      setLatestResult(null);
      return;
    }
    let cancelled = false;
    setLatestLoading(true);
    getRun(latestDone.run_id)
      .then((r) => {
        if (!cancelled) setLatestResult(r.result);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLatestLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [latestDone?.run_id]);

  const verification = latestResult?.verification;
  const trusted = verification ? verification.trusted : null;

  return (
    <div>
      <div className="content__heading">
        <h1>Command Center</h1>
        <p>System status and the most recent optimization run over the historical grid dataset.</p>
      </div>

      <div className="dataset-badge-row">
        <span className={`status-pill ${backendStatus === "online" ? "status-pill--good" : "status-pill--offline"}`}>
          <span className="status-pill__dot" />
          Backend {backendStatus === "online" ? "online" : backendStatus === "offline" ? "offline" : "checking"}
        </span>
        <span className="status-pill status-pill--historical">
          <Icon name="layers" size={13} />
          Historical Simulation (2017&ndash;2019)
        </span>
        {latestAny && (
          <span className="status-pill status-pill--idle">
            <Icon name="activity" size={13} />
            {runs.length} run{runs.length === 1 ? "" : "s"} recorded
          </span>
        )}
      </div>

      <section className="panel panel--control section-gap" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 14 }}>
        <div>
          <h2 style={{ margin: "0 0 4px" }}>Run a new optimization</h2>
          <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
            Forecast demand, detect renewable anomalies, and compute a curtailment-minimizing dispatch plan for a chosen window.
          </p>
        </div>
        <Link to="/new-run" className="btn btn-primary">
          <Icon name="bolt" size={15} />
          New Optimization Run
        </Link>
      </section>

      {runsLoading && !latestAny ? (
        <div className="card">
          <p className="empty-state">
            <span className="spinner" style={{ borderColor: "var(--border-strong)", borderTopColor: "var(--accent)" }} />
            Loading run history...
          </p>
        </div>
      ) : !latestAny ? (
        <EmptyRunState title="No runs yet" hint="Kick off the first optimization run to populate the command center with real forecast, anomaly, and curtailment figures." />
      ) : (
        <>
          <section className="kpi-grid section-gap">
            <StatCard
              label="Forecast Peak Demand"
              value={fmt(latestResult?.forecast?.peak?.forecast_mw)}
              unit="MW"
              icon="trendingUp"
              tone="neutral"
              hint={latestDone ? `Run ${latestDone.run_id}` : undefined}
            />
            <StatCard
              label="Renewable Output"
              value={fmt(latestResult?.load_balance?.hours?.reduce((s, h) => s + h.renewable_mw, 0))}
              unit="MWh"
              icon="sun"
              tone="neutral"
            />
            <StatCard
              label="Curtailment Avoided"
              value={fmt(latestResult?.curtailment?.curtailment_avoided_mwh, 1)}
              unit="MWh"
              icon="scissors"
              tone="good"
            />
            <StatCard
              label="Verification"
              value={trusted == null ? "N/A" : trusted ? "Verified" : "Flagged"}
              icon="shieldCheck"
              tone={trusted == null ? "neutral" : trusted ? "good" : "critical"}
              hint={verification ? `${verification.checked_count} figures checked` : undefined}
            />
          </section>

          <section className="card section-gap">
            <div className="section-header">
              <div>
                <div className="section-header__title-row">
                  <span className="section-header__icon">
                    <Icon name="trendingUp" size={16} />
                  </span>
                  <h2>Demand Forecast Preview</h2>
                </div>
                <p className="section-header__subtitle">
                  {latestDone ? `Most recent run — as of ${latestDone.window_end}` : "No completed run yet"}
                </p>
              </div>
              <Link to="/optimization" className="btn btn-secondary">
                View full plan
              </Link>
            </div>
            {latestLoading ? (
              <p className="empty-state">Loading forecast...</p>
            ) : latestResult?.forecast?.hourly?.length ? (
              <DemandForecastChart forecast={latestResult.forecast} />
            ) : (
              <p className="empty-state">
                <Icon name="checkCircle" size={15} />
                No forecast data available for the latest run.
              </p>
            )}
          </section>

          <section className="card section-gap">
            <div className="section-header">
              <div>
                <div className="section-header__title-row">
                  <span className="section-header__icon">
                    <Icon name="layers" size={16} />
                  </span>
                  <h2>Recent Runs</h2>
                </div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn btn-secondary" onClick={refreshRuns}>
                  <Icon name="activity" size={14} />
                  Refresh
                </button>
                <Link to="/history" className="btn btn-secondary">
                  View all
                </Link>
              </div>
            </div>
            <div className="run-list">
              {runs.slice(0, 5).map((r) => (
                <Link key={r.run_id} to={`/runs/${r.run_id}`} className="run-row" style={{ textDecoration: "none" }}>
                  <div>
                    <span className="run-row__label">Run</span>
                    <span className="run-row__value">{r.run_id}</span>
                  </div>
                  <div>
                    <span className="run-row__label">As of</span>
                    <span className="run-row__value">{r.window_end}</span>
                  </div>
                  <div>
                    <span className="run-row__label">Peak MW</span>
                    <span className="run-row__value">{fmt(r.peak_demand_mw)}</span>
                  </div>
                  <div>
                    <span className="run-row__label">Avoided MWh</span>
                    <span className="run-row__value">{fmt(r.curtailment_avoided_mwh, 1)}</span>
                  </div>
                  <div>
                    <span className="run-row__label">Verification</span>
                    <span className="run-row__value">{r.verification_status || "—"}</span>
                  </div>
                  <span className={`run-row__status run-row__status--${r.status}`}>{r.status}</span>
                </Link>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
