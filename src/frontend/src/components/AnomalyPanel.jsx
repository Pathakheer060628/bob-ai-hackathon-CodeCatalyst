const CATEGORY_TONE = {
  curtailment_likely: "over",
  weather_driven_low_resource: "under",
  equipment_or_availability_fault: "under",
  favorable_resource_surplus: "over",
  data_quality_anomaly: "over",
};

export default function AnomalyPanel({ anomalies }) {
  if (!anomalies.length) {
    return (
      <div className="card">
        <h2>Renewable Performance Anomalies</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>
          No sustained anomalies detected across solar, onshore wind, or offshore wind in this window.
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>Renewable Performance Anomalies &amp; Root Causes</h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>Asset</th>
            <th>Direction</th>
            <th>Duration</th>
            <th>Avg deviation</th>
            <th>Root cause</th>
          </tr>
        </thead>
        <tbody>
          {anomalies.map((a, i) => (
            <tr key={i}>
              <td style={{ textTransform: "capitalize" }}>{a.asset.replace("_", " ")}</td>
              <td>
                <span className={`chip chip--${CATEGORY_TONE[a.category] ?? "under"}`}>{a.direction}</span>
              </td>
              <td>{a.duration_hours}h</td>
              <td>{(a.avg_deviation * 100).toFixed(1)}%</td>
              <td>{a.label}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
