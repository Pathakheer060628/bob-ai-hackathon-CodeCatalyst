import Icon from "./Icon.jsx";

export default function Header({ datasetInfo, running, verified, onMenuClick }) {
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
        {datasetInfo && (
          <div className="topbar__dataset" title={`${datasetInfo.source} (${datasetInfo.license})`}>
            <Icon name="layers" size={14} />
            <span>
              {datasetInfo.source} &middot; {datasetInfo.license}
            </span>
          </div>
        )}
      </div>

      <div className="topbar__right">
        <span className={`status-pill ${running ? "status-pill--active" : "status-pill--idle"}`}>
          <span className="status-pill__dot" />
          {running ? "Live Analysis" : "Idle"}
        </span>
        {verified != null && (
          <span className={`status-pill ${verified ? "status-pill--good" : "status-pill--warning"}`}>
            <Icon name="shieldCheck" size={13} />
            {verified ? "Verified" : "Flagged"}
          </span>
        )}
        <button className="icon-btn" type="button" aria-label="Notifications">
          <Icon name="bell" size={18} />
        </button>
        <button className="icon-btn" type="button" aria-label="Settings">
          <Icon name="settings" size={18} />
        </button>
        <span className="topbar__avatar" aria-label="User">
          <Icon name="user" size={16} />
        </span>
      </div>
    </header>
  );
}
