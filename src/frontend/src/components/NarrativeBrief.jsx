import { useState } from "react";
import Icon from "./ui/Icon.jsx";

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

// The template narration provider (backend/llm/provider.py) always joins
// its parts with a blank line, each part opening with a "**Header**" line.
// We split on that same boundary purely to group the *unmodified* text
// into visually distinct sections — the text itself is never altered.
function splitSections(narrative) {
  return narrative.split(/\n\n+/).map((block) => {
    const firstLine = block.split("\n")[0] || "";
    const match = firstLine.match(/^\*\*([^*]+)\*\*/);
    return { heading: match ? match[1].replace(/:$/, "") : null, block };
  });
}

function iconFor(heading) {
  if (!heading) return "fileText";
  const h = heading.toLowerCase();
  if (h.includes("forecast")) return "trendingUp";
  if (h.includes("renewable") || h.includes("anomal")) return "sun";
  if (h.includes("load")) return "battery";
  if (h.includes("curtail")) return "scissors";
  return "fileText";
}

export default function NarrativeBrief({ narrative, provider }) {
  const sections = splitSections(narrative);
  const [openMap, setOpenMap] = useState(() => Object.fromEntries(sections.map((_, i) => [i, true])));

  const toggle = (i) => setOpenMap((m) => ({ ...m, [i]: !m[i] }));

  return (
    <div className="card">
      <div className="section-header">
        <div>
          <div className="section-header__title-row">
            <span className="section-header__icon">
              <Icon name="fileText" size={16} />
            </span>
            <h2>Operator Brief</h2>
          </div>
          {provider && <p className="section-header__subtitle">Narrated by {provider}</p>}
        </div>
      </div>

      <div className="brief">
        {sections.map(({ heading, block }, i) => {
          const lines = block.split("\n");
          const open = openMap[i] !== false;
          return (
            <div className="brief__section" key={i}>
              <button type="button" className="brief__section-head" onClick={() => toggle(i)}>
                <span className="brief__section-icon">
                  <Icon name={iconFor(heading)} size={13} />
                </span>
                {heading || `Section ${i + 1}`}
                <span className={`brief__section-chevron ${open ? "brief__section-chevron--open" : ""}`}>
                  <Icon name="chevronRight" size={15} />
                </span>
              </button>
              {open && (
                <div className="brief__section-body">
                  <div className="narrative">{lines.map((line, j) => renderLine(line, j))}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
