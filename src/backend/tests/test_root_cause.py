import numpy as np
import pandas as pd

from backend.tools.anomaly_detection import AnomalyEpisode, detect_renewable_anomalies
from backend.tools.root_cause import classify_root_cause


def _synthetic_history(days: int = 60) -> pd.DataFrame:
    hours = days * 24
    idx = pd.date_range("2024-01-01", periods=hours, freq="h", tz="UTC")
    hour = idx.hour.to_numpy()
    rng = np.random.default_rng(11)

    solar_cf = np.clip(np.sin((hour - 6) / 12 * np.pi), 0, None) * 0.7
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


def test_isolated_dip_classified_as_equipment_fault():
    df = _synthetic_history()
    window = df.iloc[-24 * 7 :].copy()
    tail = window.index[-72:]
    window.loc[tail, "wind_onshore_actual_mw"] *= 0.05
    window.loc[tail, "wind_onshore_capacity_factor"] = (
        window.loc[tail, "wind_onshore_actual_mw"] / window["wind_onshore_capacity_mw"]
    )
    window["renewable_actual_mw"] = (
        window["solar_actual_mw"] + window["wind_onshore_actual_mw"] + window["wind_offshore_actual_mw"]
    )

    result = detect_renewable_anomalies(window, df, "wind_onshore")
    assert result.episodes
    finding = classify_root_cause(result.episodes[0], window, df)
    assert finding.category == "equipment_or_availability_fault"


def test_correlated_dip_classified_as_weather():
    df = _synthetic_history()
    window = df.iloc[-24 * 7 :].copy()
    tail = window.index[-72:]
    # both onshore and offshore wind drop together -> shared weather cause
    window.loc[tail, "wind_onshore_actual_mw"] *= 0.1
    window.loc[tail, "wind_offshore_actual_mw"] *= 0.1
    window.loc[tail, "wind_onshore_capacity_factor"] = (
        window.loc[tail, "wind_onshore_actual_mw"] / window["wind_onshore_capacity_mw"]
    )
    window.loc[tail, "wind_offshore_capacity_factor"] = (
        window.loc[tail, "wind_offshore_actual_mw"] / window["wind_offshore_capacity_mw"]
    )
    window["renewable_actual_mw"] = (
        window["solar_actual_mw"] + window["wind_onshore_actual_mw"] + window["wind_offshore_actual_mw"]
    )
    # load stays at its normal (high, non-scarce) level so the drop doesn't
    # also look like an oversupply/curtailment situation

    result = detect_renewable_anomalies(window, df, "wind_onshore")
    assert result.episodes
    finding = classify_root_cause(result.episodes[0], window, df)
    assert finding.category == "weather_driven_low_resource"


def test_oversupply_classified_as_curtailment_likely():
    df = _synthetic_history()
    window = df.iloc[-24 * 7 :].copy()
    tail = window.index[-72:]
    window.loc[tail, "wind_onshore_actual_mw"] *= 0.05
    window.loc[tail, "wind_onshore_capacity_factor"] = (
        window.loc[tail, "wind_onshore_actual_mw"] / window["wind_onshore_capacity_mw"]
    )
    window["renewable_actual_mw"] = (
        window["solar_actual_mw"] + window["wind_onshore_actual_mw"] + window["wind_offshore_actual_mw"]
    )
    # make load tiny relative to total renewables -> abundant supply -> curtailment signature
    window["load_actual_mw"] = window["renewable_actual_mw"] * 0.5 + 1.0

    result = detect_renewable_anomalies(window, df, "wind_onshore")
    assert result.episodes
    finding = classify_root_cause(result.episodes[0], window, df)
    assert finding.category == "curtailment_likely"


def test_over_episode_classified_as_favorable_surplus():
    df = _synthetic_history()
    episode = AnomalyEpisode(
        asset="solar", start=df.index[100], end=df.index[101], direction="over",
        duration_hours=2, avg_deviation=0.1, peak_deviation=0.15,
    )
    finding = classify_root_cause(episode, df, df)
    assert finding.category == "favorable_resource_surplus"


def test_implausible_over_episode_classified_as_data_quality():
    df = _synthetic_history()
    episode = AnomalyEpisode(
        asset="solar", start=df.index[100], end=df.index[101], direction="over",
        duration_hours=2, avg_deviation=0.6, peak_deviation=0.9,
    )
    finding = classify_root_cause(episode, df, df)
    assert finding.category == "data_quality_anomaly"
