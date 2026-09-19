import { useRuns } from "../context/RunContext.jsx";
import { reportPdfUrl } from "../api/client.js";
import NarrativeBrief from "../components/NarrativeBrief.jsx";
import VerifierBadge from "../components/VerifierBadge.jsx";
import EmptyRunState from "../components/ui/EmptyRunState.jsx";
import Icon from "../components/ui/Icon.jsx";

export default function OperatorBrief() {
  const { activeResult, activeRunId, activeStatus, activeError } = useRuns();

  if (activeStatus === "error") {
    return (
      <div>
        <div className="content__heading">
          <h1>Verified Operator Brief</h1>
          <p>Narrated summary, independently re-verified against computed state.</p>
        </div>
        <div className="error-banner">
          <Icon name="alertTriangle" size={16} />
          {activeError || "The pipeline failed to produce a brief for this run."}
        </div>
      </div>
    );
  }

  if (!activeResult) {
    return (
      <div>
        <div className="content__heading">
          <h1>Verified Operator Brief</h1>
          <p>Narrated summary, independently re-verified against computed state.</p>
        </div>
        <EmptyRunState />
      </div>
    );
  }

  const verification = activeResult.verification;
  const trusted = verification?.trusted;

  if (activeResult.status === "blocked" || !activeResult.narrative) {
    const reasons = activeResult.data_quality?.hard_fail_reasons || [];
    return (
      <div>
        <div className="content__heading">
          <h1>Verified Operator Brief</h1>
          <p>Narrated summary, independently re-verified against computed state.</p>
        </div>
        <div className="error-banner">
          <Icon name="alertTriangle" size={16} />
          <div>
            Run {activeRunId} was blocked before a brief could be narrated: data quality failed a hard check.
            {reasons.length > 0 && (
              <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                {reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="content__heading">
        <h1>Verified Operator Brief</h1>
        <p>
          Run {activeRunId} &middot; narrated by {activeResult.narration_provider}. The narrator only phrases already-computed
          numbers; the badge below reflects an independent re-check, never the narrator's own claim.
        </p>
      </div>

      <section className={`panel section-gap ${trusted === false ? "" : ""}`} style={trusted === false ? { borderColor: "color-mix(in srgb, var(--status-critical) 40%, transparent)" } : undefined}>
        <div className="verify-panel">
          <VerifierBadge verification={verification} />
          <div className="export-bar" style={{ margin: 0 }}>
            <a href={reportPdfUrl(activeRunId)} target="_blank" rel="noreferrer">
              <span className="btn btn-secondary">
                <Icon name="download" size={15} />
                Export PDF brief
              </span>
            </a>
          </div>
        </div>
        {trusted === false && (
          <p style={{ marginTop: 12, marginBottom: 0, fontSize: 13, color: "var(--status-critical)", display: "flex", gap: 8, alignItems: "flex-start" }}>
            <Icon name="alertTriangle" size={15} />
            {verification.unverified_numbers.length} number(s) in the narrated brief could not be traced back to computed
            state. Treat this brief as unverified until reviewed.
          </p>
        )}
      </section>

      <NarrativeBrief narrative={activeResult.narrative} provider={activeResult.narration_provider} />
    </div>
  );
}
