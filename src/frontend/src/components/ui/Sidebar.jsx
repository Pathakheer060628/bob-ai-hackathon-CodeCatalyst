import { NavLink } from "react-router-dom";
import Icon from "./Icon.jsx";

const NAV_ITEMS = [
  { to: "/", label: "Command Center", icon: "grid", end: true },
  { to: "/new-run", label: "New Run", icon: "bolt" },
  { to: "/anomalies", label: "Anomaly Intelligence", icon: "sun" },
  { to: "/optimization", label: "Optimization Plan", icon: "battery" },
  { to: "/curtailment", label: "Curtailment Impact", icon: "scissors" },
  { to: "/regional", label: "Regional Distribution", icon: "tower" },
  { to: "/brief", label: "Operator Brief", icon: "fileText" },
  { to: "/history", label: "Run History", icon: "layers" },
];

export default function Sidebar({ open, collapsed, onNavigate, onToggleCollapse, backendOnline }) {
  return (
    <aside className={`sidebar ${open ? "sidebar--open" : ""} ${collapsed ? "sidebar--collapsed" : ""}`}>
      <nav className="sidebar__nav">
        <span className="sidebar__section-label">Navigate</span>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) => `sidebar__item nav-link ${isActive ? "sidebar__item--active" : ""}`}
          >
            <Icon name={item.icon} size={17} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div>
        <button type="button" className="sidebar__collapse-btn" onClick={onToggleCollapse}>
          <Icon name={collapsed ? "menu" : "chevronRight"} size={15} style={{ transform: collapsed ? "none" : "rotate(180deg)" }} />
          {!collapsed && <span>Collapse</span>}
        </button>
        <div className="sidebar__footer">
          <span className="sidebar__footer-dot" style={{ background: backendOnline ? "var(--status-good)" : "var(--status-critical)" }} />
          <span>{backendOnline ? "Backend reachable" : "Backend unreachable"}</span>
        </div>
      </div>
    </aside>
  );
}
