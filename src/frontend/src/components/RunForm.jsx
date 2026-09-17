import { useState } from "react";
import Icon from "./ui/Icon.jsx";

const ADVANCED_FIELDS = [
  { key: "dispatchable_capacity_mw", label: "Dispatchable capacity (MW)", step: "any" },
  { key: "storage_capacity_mwh", label: "Storage capacity (MWh)", step: "any" },
  { key: "storage_max_rate_mw", label: "Storage max charge/discharge rate (MW)", step: "any" },
  { key: "storage_efficiency", label: "Storage round-trip efficiency (0-1)", step: "0.01", min: 0, max: 1 },
  { key: "storage_initial_soc_mwh", label: "Storage initial state of charge (MWh)", step: "any" },
  { key: "max_demand_response_fraction", label: "Max demand response fraction (0-1)", step: "0.01", min: 0, max: 1 },
];

export default function RunForm({ datasetInfo, onSubmit, disabled }) {
  const defaultEnd = datasetInfo ? datasetInfo.end.slice(0, 16) : "";
  const [windowEnd, setWindowEnd] = useState(defaultEnd);
  const [lookbackDays, setLookbackDays] = useState(30);
  const [horizonHours, setHorizonHours] = useState(24);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [advanced, setAdvanced] = useState({});

  const handleAdvancedChange = (key, value) => {
    setAdvanced((prev) => {
      const next = { ...prev };
      if (value === "") delete next[key];
      else next[key] = Number(value);
      return next;
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const loadBalanceConfig = Object.keys(advanced).length > 0 ? advanced : undefined;
    onSubmit({
      windowEnd: windowEnd || defaultEnd,
      lookbackDays: Number(lookbackDays),
      horizonHours: Number(horizonHours),
      loadBalanceConfig,
    });
  };

  return (
    <form className="run-form-wrap" onSubmit={handleSubmit}>
      <div className="run-form">
        <div className="run-form__field">
          <label htmlFor="window-end">
            <Icon name="activity" size={14} />
            Analysis "as of" time
          </label>
          <input
            id="window-end"
            type="datetime-local"
            value={windowEnd || defaultEnd}
            min={datasetInfo?.start.slice(0, 16)}
            max={datasetInfo?.end.slice(0, 16)}
            onChange={(e) => setWindowEnd(e.target.value)}
          />
        </div>
        <div className="run-form__field">
          <label htmlFor="lookback">
            <Icon name="layers" size={14} />
            Lookback window (days)
          </label>
          <input
            id="lookback"
            type="number"
            min={7}
            max={365}
            value={lookbackDays}
            onChange={(e) => setLookbackDays(e.target.value)}
          />
        </div>
        <div className="run-form__field">
          <label htmlFor="horizon">
            <Icon name="trendingUp" size={14} />
            Forecast horizon (hours)
          </label>
          <input
            id="horizon"
            type="number"
            min={1}
            max={72}
            value={horizonHours}
            onChange={(e) => setHorizonHours(e.target.value)}
          />
        </div>
        <div className="run-form__submit">
          <button className="btn btn-primary" type="submit" disabled={disabled}>
            {disabled ? (
              <>
                <span className="spinner" />
                Running...
              </>
            ) : (
              <>
                <Icon name="bolt" size={15} />
                Run Optimisation
              </>
            )}
          </button>
        </div>
      </div>

      <button type="button" className="toggle-table" onClick={() => setShowAdvanced((s) => !s)} style={{ marginTop: 14 }}>
        <Icon name={showAdvanced ? "minus" : "plus"} size={13} />
        {showAdvanced ? "Hide advanced load-balancing constraints" : "Advanced load-balancing constraints"}
      </button>

      {showAdvanced && (
        <div className="run-form" style={{ marginTop: 10 }}>
          {ADVANCED_FIELDS.map((f) => (
            <div className="run-form__field" key={f.key}>
              <label htmlFor={f.key}>{f.label}</label>
              <input
                id={f.key}
                type="number"
                step={f.step}
                min={f.min}
                max={f.max}
                placeholder="auto"
                value={advanced[f.key] ?? ""}
                onChange={(e) => handleAdvancedChange(f.key, e.target.value)}
                disabled={disabled}
              />
            </div>
          ))}
        </div>
      )}
    </form>
  );
}
