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
from backend.tools.load_balancing import COST_CURTAIL_PER_MWH, COST_DISPATCH_PER_MWH

# Which installed-capacity column backs each asset's capacity-factor deviation,
# so a deviation (a fraction) can be converted into an actual MW magnitude.
ASSET_CAPACITY_COLUMNS = {
    "solar": "solar_capacity_mw",
    "wind_onshore": "wind_onshore_capacity_mw",
    "wind_offshore": "wind_offshore_capacity_mw",
}

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

# One concrete, actionable recommendation per root-cause category -- every
# anomaly finding gets a "what should an operator actually do about this",
# not just a label for what happened.
ROOT_CAUSE_RECOMMENDATIONS = {
    "curtailment_likely": (
        "Issue a curtailment order for this asset during the episode window, or shift the surplus into "
        "storage/demand response if available -- the LP curtailment plan already prices this trade-off."
    ),
    "weather_driven_low_resource": (
        "No asset-specific fix -- this is a shared weather lull. Cover the shortfall from dispatchable "
        "generation (see the load-balancing plan) and treat it as expected seasonal variability, not a fault."
    ),
    "equipment_or_availability_fault": (
        "Dispatch a technical/SCADA check for this asset -- isolated underperformance while other assets "
        "track normal is the signature of a turbine trip, inverter fault, or unplanned outage."
    ),
    "favorable_resource_surplus": (
        "Benign for now, but monitor: sustained overperformance raises near-term curtailment risk. Pre-stage "
        "storage headroom or demand-response capacity ahead of the next forecast run."
    ),
    "data_quality_anomaly": (
        "Verify the underlying meter/telemetry feed for this asset before acting on it -- the deviation "
        "magnitude is outside physically plausible bounds, more likely a data artefact than real output."
    ),
    "unknown": (
        "Insufficient evidence to recommend a specific action -- flag for manual operator review rather than "
        "an automated response."
    ),
}


@dataclass
class RootCauseFinding:
    episode: AnomalyEpisode
    category: str
    label: str
    evidence: dict
    confidence: float = 0.5
    estimated_cost_usd: float = 0.0
    cost_basis: str = ""
    recommended_action: str = ""


def _estimate_cost_impact_usd(episode: AnomalyEpisode, window: pd.DataFrame) -> tuple[float, str]:
    """Ballpark $ exposure for one anomaly episode, using the same illustrative
    $/MWh rates the load-balancing LP already prices actions at (backend/tools/
    load_balancing.py) -- not a new pricing model, just applying the existing
    one to an anomaly instead of a dispatch decision.

    Magnitude = deviation (a capacity-factor fraction) x the asset's actual
    installed capacity over the episode -- the real MW swing implied by the
    deviation, not just its percentage size, so a long, mild anomaly on a
    large fleet (e.g. Germany's ~44 GW onshore wind base) can rank above a
    short, severe one on a small asset.

    "under" episodes are priced at the full dispatch rate: a genuine shortfall
    has to be backfilled roughly 1:1 by dispatchable generation.

    "over" episodes are priced at the curtailment rate, but only for the
    share of that excess actually likely to need curtailment rather than just
    being absorbed by ordinary demand: scaled by the episode's own
    renewable-to-load ratio (0-1), the same signal `classify_root_cause`
    already computes to judge oversupply risk. Without this scaling, treating
    100% of a multi-day fleet-wide deviation as curtailable hugely overstates
    exposure -- e.g. a period where wind briefly ran 40% of load would price
    very differently from one where it ran 90%+ of load, even at an identical
    capacity-factor deviation.
    """
    capacity_col = ASSET_CAPACITY_COLUMNS.get(episode.asset)
    if capacity_col is None or capacity_col not in window.columns:
        return 0.0, ""
    span = window.loc[episode.start : episode.end]
    if span.empty:
        return 0.0, ""
    avg_capacity_mw = float(span[capacity_col].mean())
    magnitude_mw = abs(episode.avg_deviation) * avg_capacity_mw

    if episode.direction == "over":
        oversupply_ratio = min(1.0, _renewable_load_ratio(window, episode.start, episode.end))
        rate, basis = COST_CURTAIL_PER_MWH * oversupply_ratio, "curtailment risk"
    else:
        rate, basis = COST_DISPATCH_PER_MWH, "backfill dispatch"

    cost = magnitude_mw * episode.duration_hours * rate
    return round(cost, 2), basis


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
    cost_usd, cost_basis = _estimate_cost_impact_usd(episode, window)

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
            estimated_cost_usd=cost_usd,
            cost_basis=cost_basis,
            recommended_action=ROOT_CAUSE_RECOMMENDATIONS[category],
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
        estimated_cost_usd=cost_usd,
        cost_basis=cost_basis,
        recommended_action=ROOT_CAUSE_RECOMMENDATIONS[category],
    )
