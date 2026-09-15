import Icon from "./Icon.jsx";

const NAV_ITEMS = [
  { id: "section-overview", label: "Overview", icon: "grid" },
  { id: "section-optimization", label: "Optimization", icon: "sliders" },
  { id: "section-forecast", label: "Forecast", icon: "trendingUp" },
  { id: "section-anomalies", label: "Renewables", icon: "sun" },
  { id: "section-anomalies", label: "Anomalies", icon: "alertTriangle" },
  { id: "section-loadbalance", label: "Load Balance", icon: "battery" },
  { id: "section-curtailment", label: "Curtailment", icon: "scissors" },
  { id: "section-verification", label: "Verification", icon: "shieldCheck" },
  { id: "section-brief", label: "Reports", icon: "fileText" },
];

/** Visual navigation only: scrolls to an existing section if it is present
 * on the page. Never fabricates pages/data — items simply no-op until the
 * corresponding section has rendered (i.e. a run has produced results). */
export default function Sidebar({ availableIds, activeId, open, onNavigate }) {
  const handleClick = (id) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    onNavigate?.();
  };

  return (
    <aside className={`sidebar ${open ? "sidebar--open" : ""}`}>
      <nav className="sidebar__nav">
        {NAV_ITEMS.map((item, i) => {
          const available = availableIds.has(item.id);
          const active = available && activeId === item.id;
          return (
            <button
              key={`${item.id}-${i}`}
              type="button"
              className={`sidebar__item ${active ? "sidebar__item--active" : ""} ${!available ? "sidebar__item--disabled" : ""}`}
              onClick={() => available && handleClick(item.id)}
              disabled={!available}
            >
              <Icon name={item.icon} size={17} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="sidebar__footer">
        <span className="sidebar__footer-dot" />
        System nominal
      </div>
    </aside>
  );
}
