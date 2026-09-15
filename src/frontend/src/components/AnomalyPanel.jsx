import Icon from "./ui/Icon.jsx";

const CATEGORY_TONE = {
  curtailment_likely: "over",
  weather_driven_low_resource: "under",
  equipment_or_availability_fault: "under",
  favorable_resource_surplus: "over",
  data_quality_anomaly: "over",
};

const ASSET_ICON = {
  solar: "sun",
  wind_onshore: "wind",
  wind_offshore: "wind",
};

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { month: "2-digit", day: "2-digit", year: "numeric" });
}

export default function AnomalyPanel({ anomalies }) {
  if (!anomalies.length) {
    return (
      <div className="card">
        <div className="section-header">
          <div>
            <div className="section-header__title-row">
              <span className="section-header__icon">
                <Icon name="sun" size={16} />
              </span>
              <h2>Renewable Performance Anomalies</h2>
            </div>
          </div>
        </div>
        <p className="empty-state">
          <Icon name="checkCircle" size={15} />
          No sustained anomalies detected across solar, onshore wind, or offshore wind in this window.
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="section-header">
        <div>
          <div className="section-header__title-row">
            <span className="section-header__icon">
              <Icon name="sun" size={16} />
            </span>
            <h2>Renewable Performance Anomalies &amp; Root Causes</h2>
          </div>
          <p className="section-header__subtitle">{anomalies.length} episode(s) detected across renewable assets</p>
        </div>
      </div>

      <div className="anomaly-list">
        {anomalies.map((a, i) => {
          const tone = CATEGORY_TONE[a.category] ?? "under";
          return (
            <div className="anomaly-card" key={i}>
              <div className="anomaly-card__top">
                <span className="anomaly-card__asset">
                  <span className="anomaly-card__asset-icon">
                    <Icon name={ASSET_ICON[a.asset] || "layers"} size={14} />
                  </span>
                  {a.asset.replace(/_/g, " ")}
                </span>
                <span className={`chip chip--${tone}`}>{a.direction}performance</span>
              </div>
              <div className="anomaly-card__range">
                {formatDate(a.start)} &rarr; {formatDate(a.end)}
              </div>
              <div className="anomaly-card__stats">
                <span className="anomaly-card__stat">
                  Duration: <strong>{a.duration_hours}h</strong>
                </span>
                <span className="anomaly-card__stat">
                  Avg deviation: <strong>{(a.avg_deviation * 100).toFixed(1)}%</strong>
                </span>
                <span className="anomaly-card__stat">
                  Peak deviation: <strong>{(a.peak_deviation * 100).toFixed(1)}%</strong>
                </span>
              </div>
              <div className="anomaly-card__cause">
                <Icon name="alertTriangle" size={14} />
                <span>
                  <strong>Root Cause: </strong>
                  {a.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
