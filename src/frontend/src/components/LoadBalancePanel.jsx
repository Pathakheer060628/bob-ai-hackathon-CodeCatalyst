import { useState } from "react";
import Icon from "./ui/Icon.jsx";

export default function LoadBalancePanel({ plan }) {
  const [showAll, setShowAll] = useState(false);

  const header = (
    <div className="section-header">
      <div>
        <div className="section-header__title-row">
          <span className="section-header__icon">
            <Icon name="battery" size={16} />
          </span>
          <h2>Load-Balancing Recommendation</h2>
        </div>
      </div>
    </div>
  );

  if (!plan.feasible) {
    return (
      <div className="card">
        {header}
        <p className="empty-state" style={{ color: "var(--status-critical)" }}>
          <Icon name="alertTriangle" size={15} />
          No feasible plan found for this horizon.
        </p>
      </div>
    );
  }

  const rows = showAll ? plan.hours : plan.hours.filter((h) => h.shed_mw > 0.01 || h.discharge_mw > 0.01 || h.charge_mw > 0.01);

  return (
    <div className="card">
      {header}
      <div className="stat-row">
        <div className="stat-tile">
          <div className="stat-tile__label">Est. operating cost</div>
          <div className="stat-tile__value">${plan.total_cost.toLocaleString()}</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Demand response used</div>
          <div className="stat-tile__value">{plan.total_shed_mwh.toLocaleString()} MWh</div>
        </div>
        <div className="stat-tile">
          <div className="stat-tile__label">Unmet demand</div>
          <div className="stat-tile__value" style={{ color: plan.total_unmet_mwh > 0 ? "var(--status-critical)" : "inherit" }}>
            {plan.total_unmet_mwh.toLocaleString()} MWh
          </div>
        </div>
      </div>

      <h3 style={{ marginTop: 18 }}>
        Recommended actions{!showAll && rows.length ? ` (${rows.length} active hour${rows.length === 1 ? "" : "s"})` : ""}
      </h3>
      {rows.length === 0 ? (
        <p className="empty-state">
          <Icon name="checkCircle" size={15} />
          No storage or demand-response action needed this horizon.
        </p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Hour</th>
                <th>Demand (MW)</th>
                <th>Renewable (MW)</th>
                <th>Dispatch (MW)</th>
                <th>Charge (MW)</th>
                <th>Discharge (MW)</th>
                <th>Shed (MW)</th>
                <th>Curtail (MW)</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((h) => (
                <tr key={h.hour_index}>
                  <td>+{h.hour_index}h</td>
                  <td>{h.demand_mw.toLocaleString()}</td>
                  <td>{h.renewable_mw.toLocaleString()}</td>
                  <td>{h.dispatch_mw.toLocaleString()}</td>
                  <td>{h.charge_mw > 0 ? h.charge_mw.toLocaleString() : ""}</td>
                  <td>{h.discharge_mw > 0 ? h.discharge_mw.toLocaleString() : ""}</td>
                  <td>{h.shed_mw > 0 ? h.shed_mw.toLocaleString() : ""}</td>
                  <td>{h.curtail_mw > 0 ? h.curtail_mw.toLocaleString() : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <button className="toggle-table" onClick={() => setShowAll((s) => !s)}>
        <Icon name={showAll ? "minus" : "plus"} size={13} />
        {showAll ? "Show only active hours" : "Show all hours"}
      </button>
    </div>
  );
}
