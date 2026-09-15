import Icon from "./Icon.jsx";

/** Reusable KPI card. Purely presentational — always fed values already
 * computed elsewhere in the app; never computes anything itself. */
export default function StatCard({ label, value, unit, icon, tone = "neutral", hint }) {
  return (
    <div className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__icon">
        <Icon name={icon} size={18} />
      </div>
      <div className="stat-card__body">
        <div className="stat-card__label">{label}</div>
        <div className="stat-card__value">
          {value}
          {unit && <span className="stat-card__unit">{unit}</span>}
        </div>
        {hint && <div className="stat-card__hint">{hint}</div>}
      </div>
    </div>
  );
}
