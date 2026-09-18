import Icon from "./ui/Icon.jsx";

// Illustrative snapshot shown when no run has completed yet — same shape as
// the live data, just placeholder numbers so the diagram never looks empty.
const DEMO = {
  renewable_mw: 6.2,
  dispatch_mw: 1.2,
  charge_mw: 0,
  discharge_mw: 0,
  demand_mw: 2.4,
  curtail_mw: 0,
  soc_pct: 82,
};

function fmt(value, digits = 1) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export default function EnergyFlowDiagram({ hour, socPct }) {
  const live = !!hour;
  const data = live
    ? {
        renewable_mw: hour.renewable_mw,
        dispatch_mw: hour.dispatch_mw,
        charge_mw: hour.charge_mw,
        discharge_mw: hour.discharge_mw,
        demand_mw: hour.demand_mw,
        curtail_mw: hour.curtail_mw,
        soc_pct: socPct,
      }
    : DEMO;

  const charging = data.charge_mw > 0.01;
  const discharging = data.discharge_mw > 0.01;
  const spilling = data.curtail_mw > 0.01;
  const socClamped = data.soc_pct == null ? null : Math.max(0, Math.min(100, data.soc_pct));

  return (
    <div className={`energy-flow ${live ? "" : "energy-flow--demo"}`}>
      <svg className="energy-flow__lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <path className="energy-flow__path energy-flow__path--sun" d="M50,14 L50,25" />
        <path className="energy-flow__path energy-flow__path--panel" d="M50,36 L50,48" />
        <path className="energy-flow__path energy-flow__path--battery" d="M50,58 C50,68 18,68 18,76" />
        <path className="energy-flow__path energy-flow__path--home" d="M50,58 L50,76" />
        <path className={`energy-flow__path energy-flow__path--grid ${spilling ? "energy-flow__path--spill" : ""}`} d="M50,58 C50,68 82,68 82,76" />
      </svg>

      <div className="energy-flow__node energy-flow__node--sun">
        <span className="energy-flow__sun-glow" />
        <span className="energy-flow__sun-icon">
          <Icon name="sun" size={20} />
        </span>
      </div>

      <div className="energy-flow__node energy-flow__node--panels">
        <div className="energy-flow__panel-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <span key={i} className="energy-flow__panel-cell" style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
        <span className="energy-flow__label">Solar panels</span>
        <span className="energy-flow__value">{fmt(data.renewable_mw)} MW</span>
      </div>

      <div className="energy-flow__node energy-flow__node--inverter">
        <span className="energy-flow__inverter-pulse" />
        <span className="energy-flow__inverter-icon">
          <Icon name="bolt" size={17} />
        </span>
        <span className="energy-flow__label">Inverter</span>
      </div>

      <div className="energy-flow__outputs">
        <div className={`energy-flow__node energy-flow__node--battery ${charging ? "is-charging" : ""} ${discharging ? "is-discharging" : ""}`}>
          <Icon name="battery" size={16} />
          <span className="energy-flow__label">Battery</span>
          <div className="energy-flow__battery-bar">
            <span className="energy-flow__battery-fill" style={{ width: `${socClamped ?? 0}%` }} />
          </div>
          <span className="energy-flow__value">{socClamped != null ? `${Math.round(socClamped)}%` : "—"}</span>
        </div>

        <div className="energy-flow__node energy-flow__node--home">
          <Icon name="home" size={16} />
          <span className="energy-flow__label">Home / demand</span>
          <span className="energy-flow__value">{fmt(data.demand_mw)} MW</span>
        </div>

        <div className="energy-flow__node energy-flow__node--grid">
          <Icon name="tower" size={16} />
          <span className="energy-flow__label">Grid</span>
          <span className="energy-flow__value">
            {data.dispatch_mw >= 0 ? "+" : ""}
            {fmt(data.dispatch_mw)} MW
          </span>
        </div>
      </div>

      {!live && <span className="energy-flow__demo-badge">Illustrative — run an optimization for live numbers</span>}
    </div>
  );
}
