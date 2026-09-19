import { useState } from "react";
import { useRuns } from "../context/RunContext.jsx";
import RegionalDistributionPanel from "../components/RegionalDistributionPanel.jsx";
import EmptyRunState from "../components/ui/EmptyRunState.jsx";
import Icon from "../components/ui/Icon.jsx";

export default function RegionalDistribution() {
  const { activeResult, activeRunId, activeStatus } = useRuns();
  const [sortBy, setSortBy] = useState("unmet");

  if (!activeResult) {
    return (
      <div>
        <div className="content__heading">
          <h1>Regional Power Distribution</h1>
          <p>Population-weighted demand per region, routed from the nearest generation hub at least-cost.</p>
        </div>
        <EmptyRunState />
      </div>
    );
  }

  const regional = activeResult.regional_distribution;

  if (activeResult.status === "blocked" || !regional) {
    return (
      <div>
        <div className="content__heading">
          <h1>Regional Power Distribution</h1>
          <p>
            Run {activeRunId} &middot; {activeStatus}
          </p>
        </div>
        <div className="error-banner">
          <Icon name="alertTriangle" size={16} />
          This run was blocked before optimization ran (data-quality gate failed), so there's no regional
          distribution plan to show. Start a new run with a wider lookback window.
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="content__heading">
        <h1>Regional Power Distribution</h1>
        <p>
          Run {activeRunId} &middot; {activeStatus} &middot; peak-hour demand split by state population, routed from
          the nearest generation hub at least cost.
        </p>
      </div>

      <RegionalDistributionPanel regional={regional} sortBy={sortBy} onSortByChange={setSortBy} />
    </div>
  );
}
