import { useState } from "react";
import { useRuns } from "../context/RunContext.jsx";
import LoadBalancePanel from "../components/LoadBalancePanel.jsx";
import OptimizationChart from "../components/OptimizationChart.jsx";
import EmptyRunState from "../components/ui/EmptyRunState.jsx";
import Icon from "../components/ui/Icon.jsx";

export default function OptimizationPlan() {
  const { activeResult, activeRunId, activeStatus } = useRuns();
  const [view, setView] = useState("table");

  if (!activeResult) {
    return (
      <div>
        <div className="content__heading">
          <h1>Optimization Plan</h1>
          <p>Hour-by-hour dispatch, battery, and demand-response plan from the load-balancing LP.</p>
        </div>
        <EmptyRunState />
      </div>
    );
  }

  const plan = activeResult.load_balance;

  return (
    <div>
      <div className="content__heading">
        <h1>Optimization Plan</h1>
        <p>
          Run {activeRunId} &middot; {activeStatus} &middot; dispatch, battery, and demand-response plan from the load-balancing LP.
        </p>
      </div>

      {plan?.feasible && (
        <section className="card section-gap">
          <div className="section-header">
            <div>
              <div className="section-header__title-row">
                <span className="section-header__icon">
                  <Icon name="battery" size={16} />
                </span>
                <h2>Hourly Dispatch</h2>
              </div>
              <p className="section-header__subtitle">Toggle between the raw table and a chart view of the same hourly plan.</p>
            </div>
            <div className="view-toggle">
              <button
                type="button"
                className={`view-toggle__btn ${view === "table" ? "view-toggle__btn--active" : ""}`}
                onClick={() => setView("table")}
              >
                Table
              </button>
              <button
                type="button"
                className={`view-toggle__btn ${view === "chart" ? "view-toggle__btn--active" : ""}`}
                onClick={() => setView("chart")}
              >
                Chart
              </button>
            </div>
          </div>
          {view === "chart" && <OptimizationChart hours={plan.hours} />}
        </section>
      )}

      {(!plan?.feasible || view === "table") && <LoadBalancePanel plan={plan} />}
    </div>
  );
}
