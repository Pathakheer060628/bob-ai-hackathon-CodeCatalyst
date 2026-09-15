// Renders the narrator's **bold**-marked plain text without dangerouslySetInnerHTML.
function renderLine(line, key) {
  const parts = line.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return (
    <div key={key}>
      {parts.map((part, i) =>
        part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : <span key={i}>{part}</span>
      )}
    </div>
  );
}

export default function NarrativeBrief({ narrative, provider }) {
  const lines = narrative.split("\n");
  return (
    <div className="card">
      <h2>Operator Brief {provider && <span style={{ color: "var(--text-muted)", fontWeight: 400, fontSize: 12 }}>· narrated by {provider}</span>}</h2>
      <div className="narrative">{lines.map((line, i) => renderLine(line, i))}</div>
    </div>
  );
}
