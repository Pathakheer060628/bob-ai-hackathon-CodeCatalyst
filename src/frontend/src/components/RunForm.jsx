import { useState } from "react";
import Icon from "./ui/Icon.jsx";

export default function RunForm({ datasetInfo, onSubmit, disabled }) {
  const defaultEnd = datasetInfo ? datasetInfo.end.slice(0, 16) : "";
  const [windowEnd, setWindowEnd] = useState(defaultEnd);
  const [lookbackDays, setLookbackDays] = useState(30);
  const [horizonHours, setHorizonHours] = useState(24);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({ windowEnd: windowEnd || defaultEnd, lookbackDays: Number(lookbackDays), horizonHours: Number(horizonHours) });
  };

  return (
    <form className="run-form" onSubmit={handleSubmit}>
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
    </form>
  );
}
