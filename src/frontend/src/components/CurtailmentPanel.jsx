import Icon from "./ui/Icon.jsx";

export default function CurtailmentPanel({ curtailment }) {
  const pct = curtailment.curtailment_reduction_pct;
  return (
    <div className="card">
      <div className="section-header">
        <div>
          <div className="section-header__title-row">
            <span className="section-header__icon">
              <Icon name="scissors" size={16} />
            </span>
            <h2>Curtailment Minimization Plan</h2>
          </div>
        </div>
      </div>
      <div className="stat-row">
        <div className="stat-tile">
          <div className="stat-tile__label">Baseline curtailment</div>
          <div className="stat-tile__value">{curtailment.baseline_curtailed_mwh.toLocaleString()} MWh</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Optimized curtailment</div>
          <div className="stat-tile__value">{curtailment.optimized_curtailed_mwh.toLocaleString()} MWh</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Curtailment avoided</div>
          <div className="stat-tile__value" style={{ color: "var(--status-good)" }}>
            {curtailment.curtailment_avoided_mwh.toLocaleString()} MWh
          </div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Reduction</div>
          <div className="stat-tile__value" style={{ color: "var(--status-good)" }}>
            {pct.toFixed(1)}%
          </div>
        </div>
      </div>
    </div>
  );
}
