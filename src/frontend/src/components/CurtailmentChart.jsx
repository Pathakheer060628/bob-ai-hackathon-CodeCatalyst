// Simple two-bar comparison: baseline vs. optimized curtailed MWh, both
// straight from backend/tools/curtailment.py::minimize_curtailment (via
// serialize_curtailment) — no client-side computation.
export default function CurtailmentChart({ baseline, optimized }) {
  const max = Math.max(baseline, optimized, 1);
  const bars = [
    { label: "Baseline (no flexibility)", value: baseline, color: "var(--status-warning)" },
    { label: "Optimized plan", value: optimized, color: "var(--status-good)" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {bars.map((b) => (
        <div key={b.label}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, marginBottom: 5, color: "var(--text-secondary)" }}>
            <span>{b.label}</span>
            <strong style={{ color: "var(--text-primary)", fontVariantNumeric: "tabular-nums" }}>{b.value.toLocaleString()} MWh</strong>
          </div>
          <div style={{ background: "var(--surface-3)", borderRadius: 6, height: 14, overflow: "hidden" }}>
            <div
              style={{
                width: `${(b.value / max) * 100}%`,
                background: b.color,
                height: "100%",
                borderRadius: 6,
                transition: "width 220ms ease",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
