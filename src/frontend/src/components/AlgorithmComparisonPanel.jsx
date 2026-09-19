import Icon from "./ui/Icon.jsx";

/**
 * Renders `result.regional_algorithm_comparison` (backend/tools/
 * regional_distribution.py::compare_distribution_algorithms): the same
 * demand snapshot routed by three algorithms of increasing sophistication --
 * naive nearest-only greedy, a per-cluster proportional-fairness heuristic,
 * and the cost-optimal LP this module actually deploys -- so the LP's
 * advantage (or its trade-offs) is a measured result, not an assertion.
 */
export default function AlgorithmComparisonPanel({ comparisons }) {
  const deployed = comparisons.find((c) => c.algorithm === "lp_optimal");
  const cheapest = Math.min(...comparisons.map((c) => c.total_transmission_cost_usd));
  const fairest = Math.max(...comparisons.map((c) => c.worst_region_fulfillment_pct));

  return (
    <section className="card section-gap">
      <div className="section-header">
        <div>
          <div className="section-header__title-row">
            <span className="section-header__icon">
              <Icon name="sliders" size={16} />
            </span>
            <h2>Algorithm Comparison</h2>
          </div>
          <p className="section-header__subtitle">
            Same demand snapshot, three routing algorithms. The deployed LP minimizes total transmission cost, but a
            pure cost-minimizer can fully strand one small region while a fairness-weighted heuristic spreads a
            shortfall more evenly -- shown here rather than hidden.
          </p>
        </div>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Algorithm</th>
              <th>Fulfillment</th>
              <th>Unmet</th>
              <th>Transmission cost</th>
              <th>Worst region</th>
            </tr>
          </thead>
          <tbody>
            {comparisons.map((c) => (
              <tr key={c.algorithm} style={c.algorithm === "lp_optimal" ? { background: "var(--surface-2)" } : undefined}>
                <td>
                  {c.label}
                  {c.algorithm === "lp_optimal" && (
                    <span className="chip chip--over" style={{ marginLeft: 8 }}>
                      deployed
                    </span>
                  )}
                </td>
                <td>{c.overall_fulfillment_pct.toFixed(1)}%</td>
                <td style={{ color: c.total_unmet_mw > 0 ? "var(--status-critical)" : "inherit" }}>
                  {c.total_unmet_mw > 0 ? `${c.total_unmet_mw.toLocaleString()} MW` : "—"}
                </td>
                <td style={{ color: c.total_transmission_cost_usd === cheapest ? "var(--status-good)" : "inherit", fontWeight: c.total_transmission_cost_usd === cheapest ? 600 : 400 }}>
                  ${c.total_transmission_cost_usd.toLocaleString()}
                </td>
                <td style={{ color: c.worst_region_fulfillment_pct === fairest ? "var(--status-good)" : c.worst_region_fulfillment_pct < 50 ? "var(--status-critical)" : "inherit", fontWeight: c.worst_region_fulfillment_pct === fairest ? 600 : 400 }}>
                  {c.worst_region_fulfillment_pct.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {deployed && (
        <p className="empty-state" style={{ marginTop: 14, justifyContent: "flex-start" }}>
          <Icon name="checkCircle" size={15} />
          The deployed LP achieves the lowest total transmission cost (${deployed.total_transmission_cost_usd.toLocaleString()})
          by reallocating spare capacity across hub boundaries that the two simpler heuristics can't cross.
        </p>
      )}
    </section>
  );
}
