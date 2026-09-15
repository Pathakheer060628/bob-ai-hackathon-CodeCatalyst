import Icon from "./ui/Icon.jsx";

// Presentational-only lookup: maps a pipeline node name (as sent by the
// backend's SSE stream) to a display label + icon. Does not affect how
// progress is generated or what data is shown.
const NODE_META = {
  forecast: { label: "Forecast", icon: "trendingUp" },
  anomalies: { label: "Anomalies", icon: "alertTriangle" },
  load_balance: { label: "Load Balance", icon: "battery" },
  curtailment: { label: "Curtailment", icon: "scissors" },
  narrate: { label: "Narrative", icon: "fileText" },
  verify: { label: "Verification", icon: "shieldCheck" },
};

export default function ProgressFeed({ entries, running }) {
  if (!entries.length) return null;
  return (
    <div className="progress-feed">
      <div className="section-header">
        <div>
          <div className="section-header__title-row">
            <span className="section-header__icon">
              <Icon name="activity" size={16} />
            </span>
            <h2>Agent Progress</h2>
          </div>
          <p className="section-header__subtitle">Live execution trace from the optimisation pipeline</p>
        </div>
      </div>

      <div className="timeline">
        {entries.map((entry, i) => {
          const meta = NODE_META[entry.node] || { label: entry.node, icon: "checkCircle" };
          const isLast = i === entries.length - 1;
          return (
            <div className="timeline__item" key={i}>
              <div className="timeline__rail">
                <span className="timeline__dot">
                  <Icon name={isLast && running ? "activity" : "checkCircle"} size={13} />
                </span>
                {i < entries.length - 1 && <span className="timeline__line" />}
              </div>
              <div className="timeline__content">
                <div className="timeline__node">
                  <Icon name={meta.icon} size={12} style={{ marginRight: 6, verticalAlign: -2 }} />
                  {meta.label}
                </div>
                <div className="timeline__message">{entry.message}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
