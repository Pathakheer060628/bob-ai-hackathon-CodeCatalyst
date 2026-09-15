import numpy as np
import pandas as pd
import pytest

from backend.tools.forecasting import forecast_demand, forecast_renewable_supply


def _synthetic_load_series(weeks: int = 10) -> pd.Series:
    hours = weeks * 24 * 7
    idx = pd.date_range("2024-01-01", periods=hours, freq="h", tz="UTC")
    hour_of_day = idx.hour.to_numpy()
    daily = 40000 + 8000 * np.sin((hour_of_day - 6) / 24 * 2 * np.pi)
    weekday_boost = np.where(idx.dayofweek < 5, 2000, -1000)
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 300, size=hours)
    return pd.Series(daily + weekday_boost + noise, index=idx)


def test_forecast_demand_requires_min_history():
    short_series = _synthetic_load_series(weeks=1).iloc[:100]
    with pytest.raises(ValueError):
        forecast_demand(short_series, horizon_hours=24)


def test_forecast_demand_produces_horizon_length():
    series = _synthetic_load_series()
    result = forecast_demand(series, horizon_hours=24)
    assert len(result.hourly) == 24
    assert result.hourly[0].timestamp > series.index.max()


def test_forecast_demand_tracks_seasonal_pattern():
    series = _synthetic_load_series()
    result = forecast_demand(series, horizon_hours=24)
    peak = result.peak
    assert peak is not None
    # peak load in this synthetic profile occurs mid-afternoon/evening, not the middle of the night
    assert 10 <= peak.timestamp.hour <= 23


def test_forecast_demand_flags_injected_spike():
    series = _synthetic_load_series()
    # inject an artificial spike pattern into the trailing week so the trend factor picks it up
    series.iloc[-24:] = series.iloc[-24:] * 1.6
    result = forecast_demand(series, horizon_hours=24, spike_std_threshold=1.0)
    assert len(result.spikes) > 0
    assert result.trend_factor > 1.0


def test_forecast_demand_bounds_are_ordered():
    series = _synthetic_load_series()
    result = forecast_demand(series, horizon_hours=12)
    for h in result.hourly:
        assert h.lower_bound_mw <= h.forecast_mw <= h.upper_bound_mw


def test_forecast_demand_timestamps_are_hourly_and_aligned():
    series = _synthetic_load_series()
    horizon = 24
    result = forecast_demand(series, horizon_hours=horizon)
    timestamps = [h.timestamp for h in result.hourly]
    assert len(timestamps) == horizon
    # first forecast hour is exactly one hour after the last observed history point
    assert timestamps[0] == series.index.max() + pd.Timedelta(hours=1)
    # every subsequent hour steps forward by exactly one hour, no gaps/dupes
    for prev, nxt in zip(timestamps, timestamps[1:]):
        assert nxt - prev == pd.Timedelta(hours=1)


def test_forecast_renewable_supply_nonnegative():
    from backend.data.loader import load_grid_data

    df = load_grid_data()
    forecast = forecast_renewable_supply(df, start=df.index.max() + pd.Timedelta(hours=1), horizon_hours=24)
    assert len(forecast) == 24
    assert all(v >= 0 for v in forecast)
