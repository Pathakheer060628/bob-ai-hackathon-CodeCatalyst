import Icon from "./ui/Icon.jsx";

const VERDICT_COPY = {
  profit: { label: "Plan in Profit", color: "var(--status-good)", icon: "trendingUp" },
  breakeven: { label: "Break-even", color: "var(--text-secondary)", icon: "activity" },
  undetermined: { label: "Undetermined", color: "var(--text-secondary)", icon: "alertTriangle" },
};

/**
 * Two already-computed cost readings, shown separately rather than netted
 * into one number -- they cover different time windows (the optimization
 * value is over the forecast horizon; anomaly cost exposure is over the
 * historical lookback window) so combining them would be misleading. No new
 * pipeline stage -- everything here comes from `result.business_impact`
 * (backend/api/schemas.py::serialize_business_impact) and
 * `result.anomalies[].estimated_cost_usd`.
 */
export default function BusinessImpactPanel({ businessImpact, curtailment, anomalies }) {
  const verdict = VERDICT_COPY[businessImpact.verdict] || VERDICT_COPY.undetermined;

  const topCostAnomalies = [...anomalies]
    .filter((a) => a.estimated_cost_usd > 0)
    .sort((a, b) => b.estimated_cost_usd - a.estimated_cost_usd)
    .slice(0, 5);

  return (
    <div className="card section-gap">
      <div className="section-header">
        <div>
          <div className="section-header__title-row">
            <span className="section-header__icon">
              <Icon name="dollar" size={16} />
            </span>
            <h2>Business Impact</h2>
          </div>
          <p className="section-header__subtitle">
            What the optimized dispatch plan is worth vs. doing nothing (this forecast horizon), shown alongside the
            $ risk already identified in this run's anomalies (the historical lookback window) -- kept separate since
            they cover different time periods.
          </p>
        </div>
        <span
          className="status-pill"
          style={{ background: "transparent", border: `1px solid ${verdict.color}`, color: verdict.color }}
        >
          <Icon name={verdict.icon} size={13} />
          {verdict.label}
        </span>
      </div>

      <div className="stat-row">
        <div className="stat-tile">
          <div className="stat-tile__label">Baseline plan cost (this horizon)</div>
          <div className="stat-tile__value">
            {curtailment.baseline_total_cost_usd != null ? `$${curtailment.baseline_total_cost_usd.toLocaleString()}` : "n/a"}
          </div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Optimized plan cost (this horizon)</div>
          <div className="stat-tile__value">
            {curtailment.optimized_total_cost_usd != null ? `$${curtailment.optimized_total_cost_usd.toLocaleString()}` : "n/a"}
          </div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Optimization value (profit)</div>
          <div className="stat-tile__value" style={{ color: "var(--status-good)" }}>
            ${businessImpact.optimization_value_usd.toLocaleString()}
          </div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Anomaly cost exposure (lookback window)</div>
          <div className="stat-tile__value" style={{ color: "var(--status-warning)" }}>
            ${businessImpact.anomaly_cost_exposure_usd.toLocaleString()}
          </div>
        </div>
      </div>

      {topCostAnomalies.length > 0 && (
        <>
          <h3 style={{ marginTop: 18 }}>Highest cost-risk anomalies</h3>
          <p className="section-header__subtitle" style={{ marginTop: -6, marginBottom: 10 }}>
            Ranked by estimated $ exposure, not just severity -- a mild but long-running or large-asset anomaly can
            cost more than a sharp, short one.
          </p>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Asset</th>
                  <th>Direction</th>
                  <th>Duration</th>
                  <th>Root cause</th>
                  <th>Est. cost</th>
                </tr>
              </thead>
              <tbody>
                {topCostAnomalies.map((a, i) => (
                  <tr key={i}>
                    <td style={{ textTransform: "capitalize" }}>{a.asset.replace(/_/g, " ")}</td>
                    <td>{a.direction}performance</td>
                    <td>{a.duration_hours}h</td>
                    <td>{a.label}</td>
                    <td style={{ color: "var(--status-warning)", fontWeight: 600 }}>
                      ${a.estimated_cost_usd.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
