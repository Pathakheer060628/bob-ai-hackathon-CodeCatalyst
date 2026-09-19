import Icon from "./ui/Icon.jsx";

// The real LangGraph node names streamed by the backend (see
// backend/agents/orchestrator.py's add_node calls) -- root-cause
// classification happens inside the "anomalies" node, so it's labeled here
// rather than invented as a separate stage. This stepper only ever lights
// up a stage once an SSE progress event actually names it; it never shows
// a fabricated percentage-complete.
const STAGES = [
  { node: "forecast", label: "Forecast", icon: "trendingUp" },
  { node: "anomalies", label: "Anomalies & Root Cause", icon: "sun" },
  { node: "load_balance", label: "Load Balance", icon: "battery" },
  { node: "curtailment", label: "Curtailment", icon: "scissors" },
  { node: "regional_distribution", label: "Regional Distribution", icon: "tower" },
  { node: "narrate", label: "Narrate", icon: "fileText" },
  { node: "verify", label: "Verify", icon: "shieldCheck" },
];

export default function PipelineStepper({ seenNodes, running }) {
  const seen = new Set(seenNodes);
  const lastSeen = seenNodes[seenNodes.length - 1];

  return (
    <div className="stepper">
      {STAGES.map((stage) => {
        const isActive = stage.node === lastSeen && running;
        const isComplete = seen.has(stage.node) && (stage.node !== lastSeen || !running);
        const cls = isComplete ? "stepper__step--done" : isActive ? "stepper__step--active" : "";
        return (
          <span key={stage.node} className={`stepper__step ${cls}`}>
            <span className="stepper__step-dot" />
            <Icon name={stage.icon} size={13} />
            {stage.label}
          </span>
        );
      })}
    </div>
  );
}
