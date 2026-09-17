import { useMemo, useState } from "react";
import Icon from "./ui/Icon.jsx";

const WIDTH = 720;
const HEIGHT = 220;
const PAD = { top: 12, right: 16, bottom: 24, left: 52 };

const SERIES = [
  { key: "demand_mw", label: "Demand", color: "var(--series-1)" },
  { key: "renewable_mw", label: "Renewable", color: "var(--series-3)" },
  { key: "dispatch_mw", label: "Dispatch", color: "var(--series-2)" },
  { key: "discharge_mw", label: "Battery discharge", color: "var(--series-4)" },
];

/** Hour-by-hour dispatch/battery/demand chart for the Optimization Plan
 * page. Every series comes straight from the load-balancing LP's hourly
 * output (backend/api/schemas.py::serialize_load_balance) -- nothing here
 * is computed client-side beyond SVG coordinate scaling. */
export default function OptimizationChart({ hours }) {
  const [hoverIdx, setHoverIdx] = useState(null);

  const { xScale, yScale, yTicks, paths } = useMemo(() => {
    const allValues = hours.flatMap((h) => SERIES.map((s) => h[s.key] || 0));
    const min = Math.min(0, ...allValues);
    const max = Math.max(...allValues, 1);
    const yMin = min;
    const yMax = max + (max - min) * 0.1;

    const innerW = WIDTH - PAD.left - PAD.right;
    const innerH = HEIGHT - PAD.top - PAD.bottom;

    const xScale = (i) => PAD.left + (i / Math.max(hours.length - 1, 1)) * innerW;
    const yScale = (v) => PAD.top + innerH - ((v - yMin) / (yMax - yMin || 1)) * innerH;

    const paths = SERIES.map((s) => ({
      ...s,
      d: hours.map((h, i) => `${i === 0 ? "M" : "L"}${xScale(i)},${yScale(h[s.key] || 0)}`).join(" "),
    }));

    const step = Math.ceil((yMax - yMin) / 4 / 100) * 100 || 100;
    const yTicks = [];
    for (let v = Math.ceil(yMin / step) * step; v <= yMax; v += step) yTicks.push(v);

    return { xScale, yScale, yTicks, paths };
  }, [hours]);

  const hovered = hoverIdx !== null ? hours[hoverIdx] : null;

  return (
    <div>
      <div className="legend">
        {SERIES.map((s) => (
          <span className="legend__item" key={s.key}>
            <span className="legend__line" style={{ background: s.color }} />
            {s.label} (MW)
          </span>
        ))}
      </div>
      <svg width="100%" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Optimization dispatch chart" onMouseLeave={() => setHoverIdx(null)}>
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={WIDTH - PAD.right} y1={yScale(t)} y2={yScale(t)} stroke="var(--gridline)" strokeWidth={1} />
            <text x={PAD.left - 8} y={yScale(t) + 4} fontSize={10} fill="var(--text-muted)" textAnchor="end">
              {(t / 1000).toFixed(1)}k
            </text>
          </g>
        ))}

        {paths.map((p) => (
          <path key={p.key} d={p.d} fill="none" stroke={p.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        ))}

        {hours.map((h, i) => (
          <rect
            key={`hit-${i}`}
            x={xScale(i) - WIDTH / hours.length / 2}
            y={PAD.top}
            width={WIDTH / hours.length}
            height={HEIGHT - PAD.top - PAD.bottom}
            fill="transparent"
            onMouseEnter={() => setHoverIdx(i)}
          />
        ))}

        {hovered && (
          <line x1={xScale(hoverIdx)} x2={xScale(hoverIdx)} y1={PAD.top} y2={HEIGHT - PAD.bottom} stroke="var(--baseline)" strokeWidth={1} />
        )}
      </svg>
      <div className="chart-tooltip">
        {hovered ? (
          <>
            <Icon name="activity" size={13} />
            <strong>+{hovered.hour_index}h</strong> — demand {hovered.demand_mw.toLocaleString()} MW, renewable{" "}
            {hovered.renewable_mw.toLocaleString()} MW, dispatch {hovered.dispatch_mw.toLocaleString()} MW
          </>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>Hover the chart to inspect an hour</span>
        )}
      </div>
    </div>
  );
}
