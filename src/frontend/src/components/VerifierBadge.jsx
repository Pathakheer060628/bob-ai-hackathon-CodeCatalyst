import Icon from "./ui/Icon.jsx";

export default function VerifierBadge({ verification }) {
  const trusted = verification.trusted;
  return (
    <span className={`verifier-badge ${trusted ? "verifier-badge--trusted" : "verifier-badge--flagged"}`}>
      <span className="verifier-badge__icon">
        <Icon name={trusted ? "shieldCheck" : "alertTriangle"} size={17} />
      </span>
      {trusted ? (
        <span>
          Verified
          <span className="verifier-badge__sub"> — {verification.checked_count} figures traced to computed state</span>
        </span>
      ) : (
        <span>{verification.unverified_numbers.length} unverified number(s) flagged</span>
      )}
    </span>
  );
}
