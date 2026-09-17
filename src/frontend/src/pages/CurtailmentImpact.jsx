import { useRuns } from "../context/RunContext.jsx";
import CurtailmentPanel from "../components/CurtailmentPanel.jsx";
import CurtailmentChart from "../components/CurtailmentChart.jsx";
import EmptyRunState from "../components/ui/EmptyRunState.jsx";
import Icon from "../components/ui/Icon.jsx";

export default function CurtailmentImpact() {
  const { activeResult, activeRunId, activeStatus } = useRuns();

  if (!activeResult) {
    return (
      <div>
        <div className="content__heading">
          <h1>Curtailment Impact</h1>
          <p>Baseline vs. optimized curtailed renewable output, and the MWh avoided by the plan.</p>
        </div>
        <EmptyRunState />
      </div>
    );
  }

  const curtailment = activeResult.curtailment;

  return (
    <div>
      <div className="content__heading">
        <h1>Curtailment Impact</h1>
        <p>
          Run {activeRunId} &middot; {activeStatus} &middot; baseline (no flexibility) vs. optimized curtailment.
        </p>
      </div>

      <section className="card section-gap">
        <div className="section-header">
          <div>
            <div className="section-header__title-row">
              <span className="section-header__icon">
                <Icon name="scissors" size={16} />
              </span>
              <h2>Baseline vs. Optimized</h2>
            </div>
            <p className="section-header__subtitle">Same underlying LP, run once with no flexibility and once with the full configured plan.</p>
          </div>
        </div>
        <CurtailmentChart baseline={curtailment.baseline_curtailed_mwh} optimized={curtailment.optimized_curtailed_mwh} />
      </section>

      <CurtailmentPanel curtailment={curtailment} />
    </div>
  );
}
