import { useMemo, useState } from "react";
import { useRuns } from "../context/RunContext.jsx";
import AnomalyPanel from "../components/AnomalyPanel.jsx";
import EmptyRunState from "../components/ui/EmptyRunState.jsx";
import Icon from "../components/ui/Icon.jsx";

const ASSET_FILTERS = [
  { key: "all", label: "All assets" },
  { key: "solar", label: "Solar" },
  { key: "wind_onshore", label: "Onshore Wind" },
  { key: "wind_offshore", label: "Offshore Wind" },
];

export default function AnomalyIntelligence() {
  const { activeResult, activeRunId, activeStatus } = useRuns();
  const [filter, setFilter] = useState("all");

  const anomalies = activeResult?.anomalies || [];
  const filtered = useMemo(
    () => (filter === "all" ? anomalies : anomalies.filter((a) => a.asset === filter)),
    [anomalies, filter]
  );

  if (!activeResult) {
    return (
      <div>
        <div className="content__heading">
          <h1>Renewable Anomaly Intelligence</h1>
          <p>Expected-vs-actual renewable performance and root-cause classification.</p>
        </div>
        <EmptyRunState />
      </div>
    );
  }

  return (
    <div>
      <div className="content__heading">
        <h1>Renewable Anomaly Intelligence</h1>
        <p>
          Run {activeRunId} &middot; {activeStatus} &middot; CUSUM-detected episodes with rule-based root cause classification.
        </p>
      </div>

      <div className="filter-row">
        {ASSET_FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            className={`filter-chip ${filter === f.key ? "filter-chip--active" : ""}`}
            onClick={() => setFilter(f.key)}
          >
            <Icon name={f.key === "solar" ? "sun" : f.key === "all" ? "grid" : "wind"} size={13} />
            {f.label}
            {f.key !== "all" && <span style={{ opacity: 0.7 }}> ({anomalies.filter((a) => a.asset === f.key).length})</span>}
          </button>
        ))}
      </div>

      <AnomalyPanel
        anomalies={filtered}
        emptyMessage={
          filter === "all"
            ? undefined
            : `No sustained anomalies detected for ${ASSET_FILTERS.find((f) => f.key === filter)?.label} in this window.`
        }
      />
    </div>
  );
}
