import numpy as np
import pandas as pd
import pytest

from backend.tools.anomaly_detection import detect_renewable_anomalies


def _synthetic_history(days: int = 60) -> pd.DataFrame:
    hours = days * 24
    idx = pd.date_range("2024-01-01", periods=hours, freq="h", tz="UTC")
    hour = idx.hour.to_numpy()
    # solar: daylight bell curve, capacity factor in [0, ~0.7]
    solar_cf = np.clip(np.sin((hour - 6) / 12 * np.pi), 0, None) * 0.7
    rng = np.random.default_rng(7)
    solar_cf = np.clip(solar_cf + rng.normal(0, 0.02, size=hours), 0, 1)

    onshore_cf = np.clip(0.35 + rng.normal(0, 0.05, size=hours), 0, 1)
    offshore_cf = np.clip(0.45 + rng.normal(0, 0.05, size=hours), 0, 1)

    solar_capacity = np.full(hours, 40000.0)
    onshore_capacity = np.full(hours, 35000.0)
    offshore_capacity = np.full(hours, 2500.0)

    df = pd.DataFrame(
        {
            "solar_capacity_mw": solar_capacity,
            "solar_actual_mw": solar_cf * solar_capacity,
            "solar_capacity_factor": solar_cf,
            "wind_onshore_capacity_mw": onshore_capacity,
            "wind_onshore_actual_mw": onshore_cf * onshore_capacity,
            "wind_onshore_capacity_factor": onshore_cf,
            "wind_offshore_capacity_mw": offshore_capacity,
            "wind_offshore_actual_mw": offshore_cf * offshore_capacity,
            "wind_offshore_capacity_factor": offshore_cf,
        },
        index=idx,
    )
    df["wind_capacity_mw"] = onshore_capacity + offshore_capacity
    df["wind_actual_mw"] = df["wind_onshore_actual_mw"] + df["wind_offshore_actual_mw"]
    df["renewable_actual_mw"] = df["solar_actual_mw"] + df["wind_actual_mw"]
    df["load_actual_mw"] = np.full(hours, 50000.0)
    return df


def test_no_anomalies_in_stable_history():
    df = _synthetic_history()
    window = df.iloc[-24 * 7 :]
    result = detect_renewable_anomalies(window, df, "solar")
    assert result.asset == "solar"
    assert len(result.episodes) == 0


def test_sustained_underperformance_is_detected():
    df = _synthetic_history()
    window = df.iloc[-24 * 7 :].copy()
    # knock onshore wind down to near-zero for 3 consecutive days -> sustained underperformance
    window.loc[window.index[-72:], "wind_onshore_actual_mw"] *= 0.05
    window.loc[window.index[-72:], "wind_onshore_capacity_factor"] = (
        window.loc[window.index[-72:], "wind_onshore_actual_mw"] / window["wind_onshore_capacity_mw"]
    )
    result = detect_renewable_anomalies(window, df, "wind_onshore")
    assert len(result.episodes) >= 1
    assert any(ep.direction == "under" for ep in result.episodes)


def test_single_hour_blip_does_not_trigger_cusum():
    df = _synthetic_history()
    window = df.iloc[-24 * 7 :].copy()
    # a single hour dip should not be enough for a sustained CUSUM alert
    window.loc[window.index[-1], "solar_actual_mw"] *= 0.3
    window.loc[window.index[-1], "solar_capacity_factor"] = (
        window.loc[window.index[-1], "solar_actual_mw"] / window["solar_capacity_mw"].iloc[-1]
    )
    result = detect_renewable_anomalies(window, df, "solar")
    assert len(result.episodes) == 0


def test_unknown_asset_raises():
    df = _synthetic_history()
    with pytest.raises(ValueError):
        detect_renewable_anomalies(df.iloc[-24:], df, "coal")
