export default function ProgressFeed({ entries }) {
  if (!entries.length) return null;
  return (
    <div className="progress-feed">
      <h3>Agent Progress</h3>
      <ul>
        {entries.map((entry, i) => (
          <li key={i}>
            <span className="progress-feed__node">{entry.node}</span>
            <span className="progress-feed__message">{entry.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
