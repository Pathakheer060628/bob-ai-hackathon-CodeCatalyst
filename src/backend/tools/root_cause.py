"""Rule-based root-cause classification for renewable anomaly episodes.

Each anomaly episode (from anomaly_detection.detect_renewable_anomalies) is
classified into one of a small set of explainable categories by checking, in
priority order:

1. `curtailment_likely` -- the episode is an underperformance ("under") that
   coincides with system-wide renewable supply already covering a high share
   of load. When supply is abundant relative to demand, a deliberate
   curtailment order is the most likely explanation for one asset class
   running below its expected output.
2. `weather_driven_low_resource` -- the *other* renewable asset classes were
   also depressed relative to their own seasonal expectation during the same
   window, indicating a shared weather cause (e.g. a still, overcast spell)
   rather than an asset-specific problem.
3. `equipment_or_availability_fault` -- this asset alone underperformed while
   the others tracked their seasonal norm, the signature of an isolated
   outage (turbine trip, inverter fault, curtailment at a single connection
   point, planned maintenance).
4. `favorable_resource_surplus` -- an "over" episode (actual above expected);
   benign, but flagged since it raises near-term curtailment risk.
5. `data_quality_anomaly` -- an "over" episode with an implausibly large
   deviation, more likely a data artefact than a real resource surplus.

Every classification is derived purely from the computed deviations and the
load/renewable ratio already present in the window -- no model call.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from backend.tools.anomaly_detection import ASSET_COLUMNS, AnomalyEpisode, seasonal_capacity_factor_profile

OVERSUPPLY_RATIO_THRESHOLD = 0.85
CORRELATED_WEATHER_DEVIATION_THRESHOLD = -0.10
IMPLAUSIBLE_OVER_DEVIATION = 0.5

# Below this confidence, an "equipment/availability fault" call (the elimination
# default when neither oversupply nor correlated-weather evidence is present) is
# downgraded to "unknown" rather than asserted -- a short, shallow isolated dip is
# genuinely ambiguous without an actual availability/SCADA signal to confirm it.
UNKNOWN_CONFIDENCE_FLOOR = 0.45

ROOT_CAUSE_LABELS = {
    "curtailment_likely": "Likely curtailment (renewable oversupply relative to load)",
    "weather_driven_low_resource": "Weather-driven low resource (correlated dip across asset classes)",
    "equipment_or_availability_fault": "Possible equipment or availability fault (isolated to this asset)",
    "favorable_resource_surplus": "Favorable resource surplus (benign, raises curtailment risk)",
    "data_quality_anomaly": "Data quality anomaly (implausible deviation magnitude)",
    "unknown": "Unknown -- evidence insufficient or conflicting to assign a cause",
}


@dataclass
class RootCauseFinding:
    episode: AnomalyEpisode
    category: str
    label: str
    evidence: dict
    confidence: float = 0.5


def _other_asset_avg_deviation(
    window: pd.DataFrame, full_history: pd.DataFrame, asset: str, start: pd.Timestamp, end: pd.Timestamp
) -> float:
    others = [a for a in ASSET_COLUMNS if a != asset]
    deviations = []
    span = window.loc[start:end]
    for other in others:
        column = ASSET_COLUMNS[other]
        profile = seasonal_capacity_factor_profile(full_history, column)
        for ts, row in span.iterrows():
            key = (ts.month, ts.hour)
            if key not in profile.index:
                continue
            expected = float(profile.loc[key, "expected_cf"])
            actual = float(row[column])
            deviations.append(actual - expected)
    if not deviations:
        return 0.0
    return sum(deviations) / len(deviations)


def _renewable_load_ratio(window: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> float:
    span = window.loc[start:end]
    load = span["load_actual_mw"].replace(0, pd.NA).dropna()
    if load.empty:
        return 0.0
    ratio = (span["renewable_actual_mw"] / span["load_actual_mw"]).replace([float("inf")], pd.NA).dropna()
    if ratio.empty:
        return 0.0
    return float(ratio.mean())


def classify_root_cause(
    episode: AnomalyEpisode,
    window: pd.DataFrame,
    full_history: pd.DataFrame,
) -> RootCauseFinding:
    if episode.direction == "over":
        if abs(episode.peak_deviation) > IMPLAUSIBLE_OVER_DEVIATION:
            category = "data_quality_anomaly"
            confidence = float(np.clip(0.5 + (abs(episode.peak_deviation) - IMPLAUSIBLE_OVER_DEVIATION), 0.5, 0.97))
        else:
            category = "favorable_resource_surplus"
            confidence = float(np.clip(0.9 - abs(episode.peak_deviation), 0.5, 0.9))
        return RootCauseFinding(
            episode=episode,
            category=category,
            label=ROOT_CAUSE_LABELS[category],
            evidence={"peak_deviation": episode.peak_deviation},
            confidence=round(confidence, 2),
        )

    oversupply_ratio = _renewable_load_ratio(window, episode.start, episode.end)
    other_deviation = _other_asset_avg_deviation(
        window, full_history, episode.asset, episode.start, episode.end
    )

    if oversupply_ratio >= OVERSUPPLY_RATIO_THRESHOLD:
        category = "curtailment_likely"
        margin = oversupply_ratio - OVERSUPPLY_RATIO_THRESHOLD
        confidence = float(np.clip(0.55 + margin * 2.0, 0.5, 0.97))
    elif other_deviation <= CORRELATED_WEATHER_DEVIATION_THRESHOLD:
        category = "weather_driven_low_resource"
        margin = CORRELATED_WEATHER_DEVIATION_THRESHOLD - other_deviation
        confidence = float(np.clip(0.55 + margin * 3.0, 0.5, 0.95))
    else:
        # elimination default: neither oversupply nor a correlated weather dip
        # explains it, so an isolated equipment/availability fault is the most
        # likely remaining hypothesis -- but this dataset has no direct SCADA/
        # availability signal to confirm it, so confidence scales with how
        # sustained the isolated episode is rather than being asserted outright.
        category = "equipment_or_availability_fault"
        confidence = float(np.clip(0.35 + episode.duration_hours / 48.0, 0.3, 0.75))
        if confidence < UNKNOWN_CONFIDENCE_FLOOR:
            category = "unknown"

    return RootCauseFinding(
        episode=episode,
        category=category,
        label=ROOT_CAUSE_LABELS[category],
        evidence={
            "renewable_to_load_ratio": round(oversupply_ratio, 3),
            "other_assets_avg_deviation": round(other_deviation, 4),
            "avg_deviation": episode.avg_deviation,
        },
        confidence=round(confidence, 2),
    )
