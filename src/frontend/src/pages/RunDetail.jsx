import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useRuns } from "../context/RunContext.jsx";
import StatCard from "../components/ui/StatCard.jsx";
import Icon from "../components/ui/Icon.jsx";

function fmt(value, digits = 0) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** Loads a past run (read-only, no re-run) into the shared "active run"
 * context, then offers jump links into the detail views, which all read
 * from that same context regardless of whether the run just streamed live
 * or was loaded here from history. */
export default function RunDetail() {
  const { runId } = useParams();
  const { loadRunById, activeResult, activeRunId, activeStatus, activeError } = useRuns();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    loadRunById(runId).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const isCurrent = activeRunId === runId;
  const result = isCurrent ? activeResult : null;

  return (
    <div>
      <div className="content__heading">
        <h1>Run {runId}</h1>
        <p>Loaded from the local run database &mdash; viewing stored results, not a live re-run.</p>
      </div>

      {loading ? (
        <div className="card">
          <p className="empty-state">Loading run...</p>
        </div>
      ) : isCurrent && activeStatus === "error" ? (
        <div className="error-banner">
          <Icon name="alertTriangle" size={16} />
          {activeError || "This run failed."}
        </div>
      ) : !result ? (
        <div className="card">
          <p className="empty-state">
            <Icon name="alertTriangle" size={15} />
            This run has no result yet (status: {isCurrent ? activeStatus : "unknown"}).
          </p>
        </div>
      ) : (
        <>
          <section className="kpi-grid section-gap">
            <StatCard label="Forecast Peak Demand" value={fmt(result.forecast?.peak?.forecast_mw)} unit="MW" icon="trendingUp" tone="neutral" />
            <StatCard
              label="Renewable Output"
              value={fmt(result.load_balance?.hours?.reduce((s, h) => s + h.renewable_mw, 0))}
              unit="MWh"
              icon="sun"
              tone="neutral"
            />
            <StatCard label="Curtailment Avoided" value={fmt(result.curtailment?.curtailment_avoided_mwh, 1)} unit="MWh" icon="scissors" tone="good" />
            <StatCard
              label="Verification"
              value={result.verification?.trusted ? "Verified" : "Flagged"}
              icon="shieldCheck"
              tone={result.verification?.trusted ? "good" : "critical"}
            />
          </section>

          <section className="panel section-gap">
            <h2 style={{ margin: "0 0 12px" }}>Jump to detail view</h2>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Link to="/anomalies" className="btn btn-secondary">
                <Icon name="sun" size={15} />
                Anomaly Intelligence
              </Link>
              <Link to="/optimization" className="btn btn-secondary">
                <Icon name="battery" size={15} />
                Optimization Plan
              </Link>
              <Link to="/curtailment" className="btn btn-secondary">
                <Icon name="scissors" size={15} />
                Curtailment Impact
              </Link>
              <Link to="/regional" className="btn btn-secondary">
                <Icon name="tower" size={15} />
                Regional Distribution
              </Link>
              <Link to="/brief" className="btn btn-primary">
                <Icon name="fileText" size={15} />
                Operator Brief
              </Link>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
