"""Renewable generation anomaly detection via seasonal-baseline CUSUM.

For each renewable asset class (solar, wind_onshore, wind_offshore) we build
a long-run expected capacity-factor profile from historical data (median
capacity factor per month/hour-of-day), then run a two-sided CUSUM
change-point detector over the residual (actual - expected) for the
requested window. CUSUM is used -- rather than a flat threshold -- so a
single noisy hour doesn't trigger an alert but a *sustained* drift away from
the seasonal norm does, distinguishing a real emerging performance issue
from ordinary hour-to-hour variability.

Negative episodes (actual persistently below expected) are underperformance;
positive episodes (actual persistently above expected, i.e. a supply glut)
are the signature of an oversupply situation that a curtailment order would
address -- both feed into root-cause classification downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

ASSET_COLUMNS = {
    "solar": "solar_capacity_factor",
    "wind_onshore": "wind_onshore_capacity_factor",
    "wind_offshore": "wind_offshore_capacity_factor",
}

DEFAULT_SLACK_STD = 0.5
DEFAULT_DECISION_STD = 4.0

# Hours where the seasonal-expected capacity factor is below this are treated
# as "not meaningfully generating" (e.g. solar overnight, or dawn/dusk
# transition hours) and excluded from CUSUM scoring -- noise around a
# near-zero baseline is not an operationally relevant anomaly.
MIN_MEANINGFUL_CF = 0.03


@dataclass
class AnomalyPoint:
    timestamp: pd.Timestamp
    actual_cf: float
    expected_cf: float
    deviation: float
    cusum_pos: float
    cusum_neg: float
    is_anomaly: bool
    direction: str  # "under", "over", or "none"


@dataclass
class AnomalyEpisode:
    asset: str
    start: pd.Timestamp
    end: pd.Timestamp
    direction: str
    duration_hours: int
    avg_deviation: float
    peak_deviation: float


@dataclass
class AnomalyResult:
    asset: str
    points: list[AnomalyPoint] = field(default_factory=list)
    episodes: list[AnomalyEpisode] = field(default_factory=list)


def seasonal_capacity_factor_profile(full_history: pd.DataFrame, column: str) -> pd.DataFrame:
    series = full_history[column]
    profile = series.groupby([series.index.month, series.index.hour]).agg(
        expected_cf="median", std_cf="std"
    )
    profile.index.names = ["month", "hour"]
    overall_std = float(series.std())
    profile["std_cf"] = profile["std_cf"].fillna(overall_std).clip(lower=0.01)
    return profile


def detect_renewable_anomalies(
    window: pd.DataFrame,
    full_history: pd.DataFrame,
    asset: str,
    slack_std: float = DEFAULT_SLACK_STD,
    decision_std: float = DEFAULT_DECISION_STD,
) -> AnomalyResult:
    if asset not in ASSET_COLUMNS:
        raise ValueError(f"Unknown asset '{asset}'. Expected one of {list(ASSET_COLUMNS)}")

    column = ASSET_COLUMNS[asset]
    profile = seasonal_capacity_factor_profile(full_history, column)

    points: list[AnomalyPoint] = []
    cusum_pos, cusum_neg = 0.0, 0.0
    episodes: list[AnomalyEpisode] = []
    open_episode: dict | None = None

    for ts, row in window.iterrows():
        actual_cf = float(row[column])
        key = (ts.month, ts.hour)
        if key in profile.index:
            expected_cf = float(profile.loc[key, "expected_cf"])
            std_cf = float(profile.loc[key, "std_cf"])
        else:
            expected_cf = float(full_history[column].mean())
            std_cf = float(full_history[column].std()) or 0.01

        deviation = actual_cf - expected_cf
        k = slack_std * std_cf
        h = decision_std * std_cf

        direction = "none"
        is_anomaly = False
        if expected_cf >= MIN_MEANINGFUL_CF:
            cusum_pos = max(0.0, cusum_pos + deviation - k)
            cusum_neg = min(0.0, cusum_neg + deviation + k)

            if cusum_pos > h:
                is_anomaly, direction = True, "over"
            elif cusum_neg < -h:
                is_anomaly, direction = True, "under"

        points.append(
            AnomalyPoint(
                timestamp=ts,
                actual_cf=round(actual_cf, 4),
                expected_cf=round(expected_cf, 4),
                deviation=round(deviation, 4),
                cusum_pos=round(cusum_pos, 4),
                cusum_neg=round(cusum_neg, 4),
                is_anomaly=is_anomaly,
                direction=direction,
            )
        )

        if is_anomaly:
            if open_episode and open_episode["direction"] == direction:
                open_episode["end"] = ts
                open_episode["deviations"].append(deviation)
            else:
                if open_episode:
                    episodes.append(_close_episode(asset, open_episode))
                open_episode = {"start": ts, "end": ts, "direction": direction, "deviations": [deviation]}
            # Deliberately no reset here: the CUSUM accumulator keeps running
            # (standard usage), so a genuinely sustained episode stays flagged
            # continuously and closes only once the deviation actually reverts
            # -- resetting on every triggering hour would fragment one real
            # multi-hour episode into many spurious 1-hour ones.
        elif open_episode:
            episodes.append(_close_episode(asset, open_episode))
            open_episode = None

    if open_episode:
        episodes.append(_close_episode(asset, open_episode))

    return AnomalyResult(asset=asset, points=points, episodes=episodes)


def _close_episode(asset: str, open_episode: dict) -> AnomalyEpisode:
    deviations = open_episode["deviations"]
    return AnomalyEpisode(
        asset=asset,
        start=open_episode["start"],
        end=open_episode["end"],
        direction=open_episode["direction"],
        duration_hours=len(deviations),
        avg_deviation=round(float(np.mean(deviations)), 4),
        peak_deviation=round(
            float(min(deviations)) if open_episode["direction"] == "under" else float(max(deviations)),
            4,
        ),
    )
