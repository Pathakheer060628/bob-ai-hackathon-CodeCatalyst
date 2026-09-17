import { Link } from "react-router-dom";
import { useRuns } from "../context/RunContext.jsx";
import EmptyRunState from "../components/ui/EmptyRunState.jsx";
import Icon from "../components/ui/Icon.jsx";

function fmt(value, digits = 0) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export default function RunHistory() {
  const { runs, runsLoading, refreshRuns } = useRuns();

  return (
    <div>
      <div className="content__heading">
        <h1>Run History</h1>
        <p>Every optimization run persisted to the local database. Opening a past run loads its stored result &mdash; it never re-runs the pipeline.</p>
      </div>

      <section className="card section-gap">
        <div className="section-header">
          <div>
            <div className="section-header__title-row">
              <span className="section-header__icon">
                <Icon name="layers" size={16} />
              </span>
              <h2>All runs</h2>
            </div>
            <p className="section-header__subtitle">{runs.length} run(s) recorded</p>
          </div>
          <button className="btn btn-secondary" onClick={refreshRuns}>
            <Icon name="activity" size={14} />
            Refresh
          </button>
        </div>

        {runsLoading && runs.length === 0 ? (
          <p className="empty-state">Loading...</p>
        ) : runs.length === 0 ? (
          <EmptyRunState title="No runs recorded yet" />
        ) : (
          <div className="run-list">
            {runs.map((r) => (
              <Link key={r.run_id} to={`/runs/${r.run_id}`} className="run-row" style={{ textDecoration: "none" }}>
                <div>
                  <span className="run-row__label">Run</span>
                  <span className="run-row__value">{r.run_id}</span>
                </div>
                <div>
                  <span className="run-row__label">As of</span>
                  <span className="run-row__value">{r.window_end}</span>
                </div>
                <div>
                  <span className="run-row__label">Created</span>
                  <span className="run-row__value">{r.created_at ? new Date(r.created_at).toLocaleString() : "—"}</span>
                </div>
                <div>
                  <span className="run-row__label">Peak MW</span>
                  <span className="run-row__value">{fmt(r.peak_demand_mw)}</span>
                </div>
                <div>
                  <span className="run-row__label">Avoided MWh</span>
                  <span className="run-row__value">{fmt(r.curtailment_avoided_mwh, 1)}</span>
                </div>
                <span className={`run-row__status run-row__status--${r.status}`}>{r.status}</span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
