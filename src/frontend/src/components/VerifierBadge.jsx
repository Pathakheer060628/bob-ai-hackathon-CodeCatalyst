export default function VerifierBadge({ verification }) {
  const trusted = verification.trusted;
  return (
    <span className={`verifier-badge ${trusted ? "verifier-badge--trusted" : "verifier-badge--flagged"}`}>
      <span className="verifier-badge__dot" />
      {trusted
        ? `Verified — ${verification.checked_count} figures traced to computed state`
        : `${verification.unverified_numbers.length} unverified number(s) flagged`}
    </span>
  );
}
