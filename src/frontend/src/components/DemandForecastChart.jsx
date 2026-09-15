import { useMemo, useState } from "react";

const WIDTH = 720;
const HEIGHT = 220;
const PAD = { top: 12, right: 16, bottom: 24, left: 52 };

export default function DemandForecastChart({ forecast }) {
  const [hoverIdx, setHoverIdx] = useState(null);
  const [showTable, setShowTable] = useState(false);

  const hourly = forecast.hourly;

  const { xScale, yScale, yTicks, linePath, bandPath } = useMemo(() => {
    const values = hourly.flatMap((h) => [h.upper_bound_mw, h.lower_bound_mw, h.forecast_mw]);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const yMin = min - (max - min) * 0.1;
    const yMax = max + (max - min) * 0.1;

    const innerW = WIDTH - PAD.left - PAD.right;
    const innerH = HEIGHT - PAD.top - PAD.bottom;

    const xScale = (i) => PAD.left + (i / (hourly.length - 1)) * innerW;
    const yScale = (v) => PAD.top + innerH - ((v - yMin) / (yMax - yMin)) * innerH;

    const linePath = hourly.map((h, i) => `${i === 0 ? "M" : "L"}${xScale(i)},${yScale(h.forecast_mw)}`).join(" ");

    const upperPath = hourly.map((h, i) => `${i === 0 ? "M" : "L"}${xScale(i)},${yScale(h.upper_bound_mw)}`).join(" ");
    const lowerPath = [...hourly]
      .reverse()
      .map((h, i) => `L${xScale(hourly.length - 1 - i)},${yScale(h.lower_bound_mw)}`)
      .join(" ");
    const bandPath = `${upperPath} ${lowerPath} Z`;

    const step = Math.ceil((yMax - yMin) / 4 / 1000) * 1000 || 1000;
    const yTicks = [];
    for (let v = Math.ceil(yMin / step) * step; v <= yMax; v += step) yTicks.push(v);

    return { xScale, yScale, yTicks, linePath, bandPath };
  }, [hourly]);

  const hovered = hoverIdx !== null ? hourly[hoverIdx] : null;

  return (
    <div>
      <div className="legend">
        <span className="legend__item">
          <span className="legend__line" style={{ background: "var(--series-1)" }} />
          Forecast demand
        </span>
        <span className="legend__item">
          <span className="legend__swatch" style={{ background: "var(--series-1)", opacity: 0.25 }} />
          Expected range
        </span>
        <span className="legend__item">
          <span className="legend__swatch" style={{ background: "var(--status-critical)" }} />
          Spike hour
        </span>
      </div>
      <svg
        width="100%"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="Demand forecast chart"
        onMouseLeave={() => setHoverIdx(null)}
      >
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={WIDTH - PAD.right} y1={yScale(t)} y2={yScale(t)} stroke="var(--gridline)" strokeWidth={1} />
            <text x={PAD.left - 8} y={yScale(t) + 4} fontSize={10} fill="var(--text-muted)" textAnchor="end">
              {(t / 1000).toFixed(0)}k
            </text>
          </g>
        ))}

        <path d={bandPath} fill="var(--series-1)" opacity={0.12} stroke="none" />
        <path d={linePath} fill="none" stroke="var(--series-1)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

        {hourly.map((h, i) =>
          h.is_spike ? (
            <circle
              key={i}
              cx={xScale(i)}
              cy={yScale(h.forecast_mw)}
              r={5}
              fill="var(--status-critical)"
              stroke="var(--surface-1)"
              strokeWidth={2}
            />
          ) : null
        )}

        {hourly.map((h, i) => (
          <rect
            key={`hit-${i}`}
            x={xScale(i) - (WIDTH / hourly.length) / 2}
            y={PAD.top}
            width={WIDTH / hourly.length}
            height={HEIGHT - PAD.top - PAD.bottom}
            fill="transparent"
            onMouseEnter={() => setHoverIdx(i)}
          />
        ))}

        {hovered && (
          <line
            x1={xScale(hoverIdx)}
            x2={xScale(hoverIdx)}
            y1={PAD.top}
            y2={HEIGHT - PAD.bottom}
            stroke="var(--baseline)"
            strokeWidth={1}
          />
        )}
      </svg>

      {hovered && (
        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          <strong style={{ color: "var(--text-primary)" }}>
            {new Date(hovered.timestamp).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit" })}
          </strong>{" "}
          — {hovered.forecast_mw.toLocaleString()} MW
          {hovered.is_spike && <span className="chip chip--under" style={{ marginLeft: 8 }}>spike</span>}
        </div>
      )}

      <button className="toggle-table" onClick={() => setShowTable((s) => !s)}>
        {showTable ? "Hide table view" : "View as table"}
      </button>
      {showTable && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Hour</th>
              <th>Forecast (MW)</th>
              <th>Range (MW)</th>
              <th>Spike</th>
            </tr>
          </thead>
          <tbody>
            {hourly.map((h, i) => (
              <tr key={i}>
                <td>{new Date(h.timestamp).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit" })}</td>
                <td>{h.forecast_mw.toLocaleString()}</td>
                <td>
                  {h.lower_bound_mw.toLocaleString()}–{h.upper_bound_mw.toLocaleString()}
                </td>
                <td>{h.is_spike ? "Yes" : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
