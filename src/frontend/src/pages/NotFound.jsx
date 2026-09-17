import { Link } from "react-router-dom";
import Icon from "../components/ui/Icon.jsx";

export default function NotFound() {
  return (
    <div className="card empty-card">
      <span className="empty-card__icon">
        <Icon name="alertTriangle" size={22} />
      </span>
      <h3>Page not found</h3>
      <p>That route doesn't exist in GridSentinel.</p>
      <Link to="/" className="btn btn-primary" style={{ marginTop: 8 }}>
        <Icon name="grid" size={15} />
        Back to Command Center
      </Link>
    </div>
  );
}
