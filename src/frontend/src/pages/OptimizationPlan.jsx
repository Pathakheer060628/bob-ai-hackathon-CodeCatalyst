import { useMemo, useState } from "react";
import { useRuns } from "../context/RunContext.jsx";
import LoadBalancePanel from "../components/LoadBalancePanel.jsx";
import OptimizationChart from "../components/OptimizationChart.jsx";
import EnergyFlowDiagram from "../components/EnergyFlowDiagram.jsx";
import EmptyRunState from "../components/ui/EmptyRunState.jsx";
import Icon from "../components/ui/Icon.jsx";

export default function OptimizationPlan() {
  const { activeResult, activeRunId, activeStatus } = useRuns();
  const [view, setView] = useState("table");

  const hours = activeResult?.load_balance?.hours;

  const defaultHourIndex = useMemo(() => {
    if (!hours?.length) return 0;
    const activeIdx = hours.findIndex((h) => h.charge_mw > 0.01 || h.discharge_mw > 0.01 || h.shed_mw > 0.01);
    return activeIdx >= 0 ? activeIdx : 0;
  }, [hours]);

  const [scrubIndex, setScrubIndex] = useState(defaultHourIndex);
  const selectedIndex = Math.min(scrubIndex, (hours?.length || 1) - 1);
  const selectedHour = hours?.[selectedIndex] || null;

  // No absolute storage capacity comes back from the API, so the fill level
  // is approximated against the highest state-of-charge reached in this plan.
  const socPct = useMemo(() => {
    if (!selectedHour || !hours?.length) return null;
    const capacityEstimate = Math.max(...hours.map((h) => h.soc_mwh), 1);
    return (selectedHour.soc_mwh / capacityEstimate) * 100;
  }, [selectedHour, hours]);

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

      {plan?.feasible && hours?.length > 0 && (
        <section className="card section-gap">
          <div className="section-header">
            <div>
              <div className="section-header__title-row">
                <span className="section-header__icon">
                  <Icon name="sun" size={16} />
                </span>
                <h2>Energy Flow</h2>
              </div>
              <p className="section-header__subtitle">Scrub through the horizon to see how generation, storage, and demand balance hour by hour.</p>
            </div>
            <div className="energy-flow__scrubber">
              <button
                type="button"
                className="icon-btn"
                onClick={() => setScrubIndex((i) => Math.max(0, i - 1))}
                disabled={selectedIndex === 0}
                aria-label="Previous hour"
              >
                <Icon name="chevronRight" size={15} style={{ transform: "rotate(180deg)" }} />
              </button>
              <span className="energy-flow__scrubber-label">+{selectedHour?.hour_index ?? 0}h</span>
              <button
                type="button"
                className="icon-btn"
                onClick={() => setScrubIndex((i) => Math.min(hours.length - 1, i + 1))}
                disabled={selectedIndex === hours.length - 1}
                aria-label="Next hour"
              >
                <Icon name="chevronRight" size={15} />
              </button>
            </div>
          </div>
          <input
            type="range"
            className="energy-flow__slider"
            min={0}
            max={hours.length - 1}
            value={selectedIndex}
            onChange={(e) => setScrubIndex(Number(e.target.value))}
            aria-label="Select forecast hour"
          />
          <EnergyFlowDiagram hour={selectedHour} socPct={socPct} />
        </section>
      )}

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
