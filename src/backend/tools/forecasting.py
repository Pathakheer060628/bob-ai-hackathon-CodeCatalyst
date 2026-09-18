"""Deterministic demand forecasting + spike detection.

Method: seasonal-naive baseline (median load for the same day-of-week/hour
across a trailing lookback window) adjusted by a recent trend factor, with a
band derived from the historical spread at that same hour. This is a
standard, explainable baseline for short-horizon load forecasting -- every
number here traces back to an arithmetic operation over real historical load,
never a model call.

A forecast hour is flagged as a demand spike when it exceeds the *untrended*
seasonal baseline by more than `spike_std_threshold` standard deviations,
i.e. it would be unusual even accounting for the normal weekly pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

DEFAULT_LOOKBACK_WEEKS = 8
DEFAULT_SPIKE_STD_THRESHOLD = 2.0
TREND_FACTOR_BOUNDS = (0.8, 1.3)


@dataclass
class HourlyForecast:
    timestamp: pd.Timestamp
    forecast_mw: float
    baseline_mw: float
    baseline_std_mw: float
    upper_bound_mw: float
    lower_bound_mw: float
    is_spike: bool
    spike_severity_std: float


@dataclass
class ForecastResult:
    hourly: list[HourlyForecast] = field(default_factory=list)
    trend_factor: float = 1.0
    lookback_weeks: int = DEFAULT_LOOKBACK_WEEKS
    spike_std_threshold: float = DEFAULT_SPIKE_STD_THRESHOLD

    @property
    def spikes(self) -> list[HourlyForecast]:
        return [h for h in self.hourly if h.is_spike]

    @property
    def peak(self) -> HourlyForecast | None:
        if not self.hourly:
            return None
        return max(self.hourly, key=lambda h: h.forecast_mw)


@dataclass
class BacktestResult:
    mae: float = 0.0
    rmse: float = 0.0
    mape: float | None = None
    naive_mae: float = 0.0
    improvement_pct: float = 0.0
    n_points: int = 0
    n_folds: int = 0
    horizon_hours: int = 0


def _seasonal_profile(history: pd.Series, lookback_weeks: int) -> pd.DataFrame:
    cutoff = history.index.max() - pd.Timedelta(weeks=lookback_weeks)
    windowed = history[history.index >= cutoff]
    profile = windowed.groupby([windowed.index.dayofweek, windowed.index.hour]).agg(
        median_mw="median", std_mw="std"
    )
    profile.index.names = ["dayofweek", "hour"]
    overall_std = float(windowed.std())
    profile["std_mw"] = profile["std_mw"].fillna(overall_std).clip(lower=1.0)
    return profile


def _trend_factor(history: pd.Series, profile: pd.DataFrame, recent_days: int = 7) -> float:
    cutoff = history.index.max() - pd.Timedelta(days=recent_days)
    recent = history[history.index >= cutoff]
    if recent.empty:
        return 1.0
    expected = profile.reindex(
        list(zip(recent.index.dayofweek, recent.index.hour))
    )["median_mw"]
    expected = np.asarray(expected, dtype=float)
    actual = recent.to_numpy(dtype=float)
    mask = ~np.isnan(expected) & (expected > 0)
    if mask.sum() == 0:
        return 1.0
    factor = float(actual[mask].mean() / expected[mask].mean())
    lo, hi = TREND_FACTOR_BOUNDS
    return float(np.clip(factor, lo, hi))


def forecast_demand(
    history: pd.Series,
    horizon_hours: int = 24,
    lookback_weeks: int = DEFAULT_LOOKBACK_WEEKS,
    spike_std_threshold: float = DEFAULT_SPIKE_STD_THRESHOLD,
) -> ForecastResult:
    """Forecast `horizon_hours` beyond the end of `history` (a load_actual_mw series).

    Requires at least one full week of history so the seasonal profile has
    same-hour, same-weekday observations to draw on.
    """
    if len(history) < 24 * 7:
        raise ValueError("Need at least 1 week (168 hourly points) of history to forecast")

    history = history.sort_index()
    profile = _seasonal_profile(history, lookback_weeks)
    trend = _trend_factor(history, profile)

    last_ts = history.index.max()
    future_index = pd.date_range(
        last_ts + pd.Timedelta(hours=1), periods=horizon_hours, freq="h", tz=history.index.tz
    )

    hourly: list[HourlyForecast] = []
    for ts in future_index:
        key = (ts.dayofweek, ts.hour)
        if key in profile.index:
            baseline = float(profile.loc[key, "median_mw"])
            std = float(profile.loc[key, "std_mw"])
        else:
            baseline = float(history.mean())
            std = float(history.std())

        forecast_mw = baseline * trend
        z = 1.96
        upper = forecast_mw + z * std
        lower = max(0.0, forecast_mw - z * std)

        severity = (forecast_mw - baseline) / std if std > 0 else 0.0
        is_spike = severity > spike_std_threshold

        hourly.append(
            HourlyForecast(
                timestamp=ts,
                forecast_mw=round(forecast_mw, 1),
                baseline_mw=round(baseline, 1),
                baseline_std_mw=round(std, 1),
                upper_bound_mw=round(upper, 1),
                lower_bound_mw=round(lower, 1),
                is_spike=bool(is_spike),
                spike_severity_std=round(float(severity), 2),
            )
        )

    return ForecastResult(
        hourly=hourly,
        trend_factor=round(trend, 3),
        lookback_weeks=lookback_weeks,
        spike_std_threshold=spike_std_threshold,
    )


def backtest_demand_forecast(
    history: pd.Series,
    horizon_hours: int = 24,
    n_folds: int = 4,
    lookback_weeks: int = DEFAULT_LOOKBACK_WEEKS,
    spike_std_threshold: float = DEFAULT_SPIKE_STD_THRESHOLD,
) -> BacktestResult:
    """Rolling-origin backtest of `forecast_demand` against a same-hour-last-week naive baseline.

    Repeatedly re-runs the forecast as if it were issued at an earlier cutoff, using only
    data available up to that point, then compares the forecast against what actually
    happened (still within `history`). This is the measurable accuracy check the spec
    requires before a forecast can be trusted operationally (ss5.1): MAE/RMSE plus the
    improvement over a naive baseline, not just a plausible-looking curve.
    """
    history = history.sort_index()
    min_train = 24 * 7
    usable_start = min_train
    usable_end = len(history) - horizon_hours
    if usable_end <= usable_start:
        return BacktestResult(horizon_hours=horizon_hours)

    step = max(1, (usable_end - usable_start) // max(1, n_folds))
    cutoffs = sorted({usable_start + i * step for i in range(n_folds)} | {usable_end})
    cutoffs = [c for c in cutoffs if usable_start <= c <= usable_end]

    errors: list[np.ndarray] = []
    naive_errors: list[np.ndarray] = []
    actuals: list[np.ndarray] = []
    folds_used = 0

    for cutoff_idx in cutoffs:
        train = history.iloc[:cutoff_idx]
        actual_future = history.iloc[cutoff_idx : cutoff_idx + horizon_hours]
        if len(train) < min_train or len(actual_future) < horizon_hours:
            continue

        forecast = forecast_demand(
            train, horizon_hours=horizon_hours, lookback_weeks=lookback_weeks, spike_std_threshold=spike_std_threshold
        )
        forecast_vals = np.array([h.forecast_mw for h in forecast.hourly], dtype=float)
        actual_vals = actual_future.to_numpy(dtype=float)

        naive_vals = np.array(
            [
                history.loc[ts - pd.Timedelta(weeks=1)] if (ts - pd.Timedelta(weeks=1)) in history.index else av
                for ts, av in zip(actual_future.index, actual_vals)
            ],
            dtype=float,
        )

        errors.append(forecast_vals - actual_vals)
        naive_errors.append(naive_vals - actual_vals)
        actuals.append(actual_vals)
        folds_used += 1

    if not errors:
        return BacktestResult(horizon_hours=horizon_hours)

    all_err = np.concatenate(errors)
    all_naive_err = np.concatenate(naive_errors)
    all_actual = np.concatenate(actuals)

    mae = float(np.mean(np.abs(all_err)))
    rmse = float(np.sqrt(np.mean(all_err**2)))
    naive_mae = float(np.mean(np.abs(all_naive_err)))
    nonzero = all_actual != 0
    mape = float(np.mean(np.abs(all_err[nonzero] / all_actual[nonzero])) * 100) if nonzero.any() else None
    improvement_pct = round((1 - mae / naive_mae) * 100, 1) if naive_mae > 0 else 0.0

    return BacktestResult(
        mae=round(mae, 1),
        rmse=round(rmse, 1),
        mape=round(mape, 1) if mape is not None else None,
        naive_mae=round(naive_mae, 1),
        improvement_pct=improvement_pct,
        n_points=int(all_err.size),
        n_folds=folds_used,
        horizon_hours=horizon_hours,
    )


def forecast_renewable_supply(
    full_history: pd.DataFrame,
    start: pd.Timestamp,
    horizon_hours: int,
    tz=None,
) -> list[float]:
    """Forecast total renewable (solar + wind) output for `horizon_hours` from `start`.

    Uses the long-run month/hour-of-day capacity-factor seasonal median
    (weather-driven, so day-of-week does not matter the way it does for
    demand) applied to the most recently observed installed capacity.
    """
    combined_cf = full_history["renewable_actual_mw"] / (
        full_history["solar_capacity_mw"] + full_history["wind_capacity_mw"]
    )
    profile = combined_cf.groupby([combined_cf.index.month, combined_cf.index.hour]).median()

    last_capacity = float(
        full_history["solar_capacity_mw"].iloc[-1] + full_history["wind_capacity_mw"].iloc[-1]
    )
    overall_median = float(combined_cf.median())

    future_index = pd.date_range(start, periods=horizon_hours, freq="h", tz=tz or full_history.index.tz)
    forecast = []
    for ts in future_index:
        key = (ts.month, ts.hour)
        cf = float(profile.get(key, overall_median))
        forecast.append(round(cf * last_capacity, 1))
    return forecast
