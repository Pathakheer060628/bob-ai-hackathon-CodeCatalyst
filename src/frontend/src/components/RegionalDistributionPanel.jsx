import Icon from "./ui/Icon.jsx";

const SORTERS = {
  unmet: (a, b) => b.unmet_mw - a.unmet_mw,
  population: (a, b) => b.population - a.population,
  distance: (a, b) => a.nearest_station_distance_km - b.nearest_station_distance_km,
  fulfillment: (a, b) => a.fulfillment_pct - b.fulfillment_pct,
};

const SORT_OPTIONS = [
  { key: "unmet", label: "Shortfall" },
  { key: "population", label: "Population" },
  { key: "distance", label: "Distance to hub" },
  { key: "fulfillment", label: "Fulfillment %" },
];

/**
 * Renders `result.regional_distribution` (backend/tools/regional_distribution.py
 * via backend/api/schemas.py::serialize_regional_distribution): each of
 * Germany's 16 states' population-weighted share of peak forecast demand,
 * the nearest generation hub and its distance, and the least-cost routed
 * allocation -- including a per-region fallback recommendation whenever the
 * LP couldn't fully cover that region's need from nearby capacity.
 */
export default function RegionalDistributionPanel({ regional, sortBy, onSortByChange }) {
  const rows = [...regional.regions].sort(SORTERS[sortBy] || SORTERS.unmet);
  const hasShortfall = regional.total_unmet_mw > 0.5;

  return (
    <>
      <section className="card section-gap">
        <div className="section-header">
          <div>
            <div className="section-header__title-row">
              <span className="section-header__icon">
                <Icon name="tower" size={16} />
              </span>
              <h2>National Coverage</h2>
            </div>
            <p className="section-header__subtitle">
              Least-cost routing from {regional.regions.length ? "8 regional generation hubs" : "hubs"} against this
              run's peak forecast demand.
            </p>
          </div>
          <span
            className={`status-pill ${hasShortfall ? "status-pill--offline" : "status-pill--good"}`}
            style={{ background: "transparent", border: `1px solid ${hasShortfall ? "var(--status-critical)" : "var(--status-good)"}`, color: hasShortfall ? "var(--status-critical)" : "var(--status-good)" }}
          >
            <Icon name={hasShortfall ? "alertTriangle" : "checkCircle"} size={13} />
            {hasShortfall ? "Shortfall identified" : "Fully covered"}
          </span>
        </div>

        <div className="stat-row">
          <div className="stat-tile">
            <div className="stat-tile__label">Peak demand (national)</div>
            <div className="stat-tile__value">{regional.total_demand_mw.toLocaleString()} MW</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile__label">Allocated</div>
            <div className="stat-tile__value">{regional.total_allocated_mw.toLocaleString()} MW</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile__label">Shortfall</div>
            <div className="stat-tile__value" style={{ color: hasShortfall ? "var(--status-critical)" : "inherit" }}>
              {regional.total_unmet_mw.toLocaleString()} MW
            </div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile__label">Fulfillment</div>
            <div className="stat-tile__value" style={{ color: hasShortfall ? "var(--status-warning)" : "var(--status-good)" }}>
              {regional.overall_fulfillment_pct.toFixed(1)}%
            </div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile__label">Transmission cost</div>
            <div className="stat-tile__value">${regional.total_transmission_cost_usd.toLocaleString()}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile__label">Total hub capacity</div>
            <div className="stat-tile__value">{regional.total_station_capacity_mw.toLocaleString()} MW</div>
          </div>
        </div>

        <p
          className="empty-state"
          style={{ marginTop: 14, color: hasShortfall ? "var(--status-critical)" : "var(--text-secondary)", justifyContent: "flex-start" }}
        >
          <Icon name={hasShortfall ? "alertTriangle" : "checkCircle"} size={15} />
          {regional.system_recommendation}
        </p>
      </section>

      <section className="card section-gap">
        <div className="section-header">
          <div>
            <div className="section-header__title-row">
              <span className="section-header__icon">
                <Icon name="grid" size={16} />
              </span>
              <h2>Regions</h2>
            </div>
            <p className="section-header__subtitle">Every region gets a solution, met or not -- shortfalls carry a recommended fallback.</p>
          </div>
          <div className="filter-row" style={{ margin: 0 }}>
            {SORT_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                type="button"
                className={`filter-chip ${sortBy === opt.key ? "filter-chip--active" : ""}`}
                onClick={() => onSortByChange(opt.key)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Region</th>
                <th>Population</th>
                <th>Demand</th>
                <th>Nearest hub</th>
                <th>Distance</th>
                <th>Allocated</th>
                <th>Shortfall</th>
                <th>Fulfillment</th>
                <th>Solution</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.region}>
                  <td>{r.region}</td>
                  <td>{r.population.toLocaleString()}</td>
                  <td>{r.demand_mw.toLocaleString()} MW</td>
                  <td>{r.nearest_station}</td>
                  <td>{r.nearest_station_distance_km.toLocaleString()} km</td>
                  <td>{r.allocated_mw.toLocaleString()} MW</td>
                  <td style={{ color: r.unmet_mw > 0 ? "var(--status-critical)" : "inherit" }}>
                    {r.unmet_mw > 0 ? `${r.unmet_mw.toLocaleString()} MW` : "—"}
                  </td>
                  <td>{r.fulfillment_pct.toFixed(1)}%</td>
                  <td style={{ maxWidth: 340, fontSize: 12.5, color: "var(--text-secondary)" }}>{r.recommended_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
