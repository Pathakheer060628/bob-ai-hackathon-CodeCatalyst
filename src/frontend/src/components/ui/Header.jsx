import Icon from "./Icon.jsx";

export default function Header({ datasetInfo, backendStatus, activeStatus, onMenuClick, theme, onToggleTheme }) {
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
        {backendStatus === "offline" && (
          <span className="status-pill status-pill--offline" title="The backend API is unreachable — start it to run the pipeline">
            <span className="status-pill__dot" />
            Backend offline
          </span>
        )}
        {running && (
          <span className="status-pill status-pill--active">
            <span className="status-pill__dot" />
            Pipeline running
          </span>
        )}
        <button
          type="button"
          className="theme-toggle"
          onClick={onToggleTheme}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          <Icon name={theme === "dark" ? "sun" : "moon"} size={16} />
        </button>
        <span className="topbar__avatar" aria-label="User">
          <Icon name="user" size={16} />
        </span>
      </div>
    </header>
  );
}
