import { Link } from "react-router-dom";
import Icon from "./Icon.jsx";

/** Shared "no active run yet" empty state for the detail pages
 * (Anomaly Intelligence, Optimization Plan, Curtailment Impact, Operator
 * Brief) so they never render a blank panel when nothing has run yet. */
export default function EmptyRunState({ title = "No run selected", hint }) {
  return (
    <div className="card empty-card">
      <span className="empty-card__icon">
        <Icon name="activity" size={22} />
      </span>
      <h3>{title}</h3>
      <p>{hint || "Start a new optimization run, or open a completed run from Run History, to see this view populated with real pipeline output."}</p>
      <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
        <Link to="/new-run" className="btn btn-primary">
          <Icon name="bolt" size={15} />
          New Run
        </Link>
        <Link to="/history" className="btn btn-secondary">
          <Icon name="layers" size={15} />
          Run History
        </Link>
      </div>
    </div>
  );
}
