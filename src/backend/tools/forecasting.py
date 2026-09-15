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
