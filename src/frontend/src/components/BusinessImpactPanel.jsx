import Icon from "./ui/Icon.jsx";

const VERDICT_COPY = {
  profit: { label: "Net Profit", color: "var(--status-good)", icon: "trendingUp" },
  breakeven: { label: "Break-even", color: "var(--text-secondary)", icon: "activity" },
  loss: { label: "Net Loss", color: "var(--status-critical)", icon: "alertTriangle" },
  undetermined: { label: "Undetermined", color: "var(--text-secondary)", icon: "alertTriangle" },
};

/**
 * Full run-level P&L (backend/api/schemas.py::serialize_business_impact):
 * revenue (energy actually delivered x an illustrative wholesale price)
 * against everything it costs to deliver it -- LP operating cost, prorated
 * fleet maintenance (illustrative $/MW-year O&M benchmark applied to the
 * regional-distribution hub capacity), and regional transmission cost.
 * `optimization_value_usd` / `anomaly_cost_exposure_usd` are shown
 * separately below since they cover different time windows than the
 * horizon-level P&L above them.
 */
export default function BusinessImpactPanel({ businessImpact, anomalies }) {
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
            <h2>Business Impact &amp; Profit/Loss</h2>
          </div>
          <p className="section-header__subtitle">
            Revenue from energy actually delivered this horizon (${businessImpact.wholesale_price_usd_per_mwh}/MWh
            illustrative wholesale price), against operating cost, prorated fleet maintenance (${businessImpact.maintenance_rate_usd_per_mw_year.toLocaleString()}/MW-year
            blended O&amp;M benchmark), and regional transmission cost.
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
          <div className="stat-tile__label">Revenue ({businessImpact.mwh_served.toLocaleString()} MWh delivered)</div>
          <div className="stat-tile__value">${businessImpact.revenue_usd.toLocaleString()}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Operating cost</div>
          <div className="stat-tile__value">${businessImpact.operating_cost_usd.toLocaleString()}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Maintenance cost</div>
          <div className="stat-tile__value">${businessImpact.maintenance_cost_usd.toLocaleString()}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Transmission cost</div>
          <div className="stat-tile__value">${businessImpact.transmission_cost_usd.toLocaleString()}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Total cost</div>
          <div className="stat-tile__value">${businessImpact.total_cost_usd.toLocaleString()}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Net profit</div>
          <div className="stat-tile__value" style={{ color: verdict.color }}>
            ${businessImpact.net_profit_usd.toLocaleString()}
            {businessImpact.profit_margin_pct != null && (
              <span style={{ fontSize: 13, fontWeight: 400, color: "var(--text-secondary)" }}> ({businessImpact.profit_margin_pct}%)</span>
            )}
          </div>
        </div>
      </div>

      <div className="stat-row" style={{ marginTop: 4 }}>
        <div className="stat-tile">
          <div className="stat-tile__label">Optimization value (vs. no flexibility)</div>
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
