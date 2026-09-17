import Icon from "./Icon.jsx";

export default function Header({ datasetInfo, backendStatus, activeStatus, activeVerified, onMenuClick }) {
  const running = activeStatus === "running" || activeStatus === "pending";
  return (
    <header className="topbar">
      <div className="topbar__left">
        <button className="topbar__menu-btn" type="button" aria-label="Toggle navigation" onClick={onMenuClick}>
          <Icon name="menu" size={20} />
        </button>
        <div className="topbar__brand">
          <span className="topbar__brand-mark">
            <Icon name="bolt" size={18} />
          </span>
          <div>
            <div className="topbar__title">GridSentinel</div>
            <div className="topbar__subtitle">Grid Optimization &amp; Renewable Intelligence</div>
          </div>
        </div>
      </div>

      <div className="topbar__center">
        <div className="dataset-badge-row" style={{ marginBottom: 0 }}>
          <span className="status-pill status-pill--historical" title="This system runs against a fixed historical extract, never live telemetry">
            <Icon name="layers" size={13} />
            Historical Simulation (2017&ndash;2019)
          </span>
          {datasetInfo && (
            <div className="topbar__dataset" title={`${datasetInfo.source} (${datasetInfo.license})`}>
              <Icon name="fileText" size={14} />
              <span>
                {datasetInfo.source} &middot; {datasetInfo.license}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="topbar__right">
        <span className={`status-pill ${backendStatus === "online" ? "status-pill--good" : backendStatus === "offline" ? "status-pill--offline" : "status-pill--idle"}`}>
          <span className="status-pill__dot" />
          {backendStatus === "online" ? "Backend online" : backendStatus === "offline" ? "Backend offline" : "Checking..."}
        </span>
        {running && (
          <span className="status-pill status-pill--active">
            <span className="status-pill__dot" />
            Pipeline running
          </span>
        )}
        {activeVerified != null && !running && (
          <span className={`status-pill ${activeVerified ? "status-pill--good" : "status-pill--warning"}`}>
            <Icon name="shieldCheck" size={13} />
            {activeVerified ? "Verified" : "Flagged"}
          </span>
        )}
        <span className="topbar__avatar" aria-label="User">
          <Icon name="user" size={16} />
        </span>
      </div>
    </header>
  );
}
