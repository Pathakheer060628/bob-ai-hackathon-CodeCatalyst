"""Leakage-safe feature engineering for the trained demand-forecasting model.

Every feature for a (origin_ts, horizon_h) training row is computable using
only data available *at* origin_ts -- nothing from between origin_ts and the
target timestamp (origin_ts + horizon_h hours) ever enters a feature. This
mirrors how the model is actually used at inference time: given history up
to "now", predict `horizon_h` hours ahead.

Two families of feature:
  - autocorrelation / trend: rolling means/std of load ending at origin_ts,
    plus the load exactly 168h (1 week) and 336h (2 weeks) *before the
    target* -- both are always inside "known history" for any horizon up to
    72h, since 72 < 168.
  - calendar + weather-proxy: cyclical encodings of the target timestamp's
    hour/day-of-week/month, plus a seasonal renewable capacity-factor
    climatology looked up for the target's (month, hour) -- the same
    weather-proxy approach already used by
    `backend.tools.forecasting.forecast_renewable_supply`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "horizon_h",
    "roll_mean_24",
    "roll_mean_168",
    "roll_std_168",
    "lag_168",
    "lag_336",
    "trend_ratio",
    "renewable_cf_expected",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "month_sin",
    "month_cos",
    "is_weekend",
]

TARGET_COLUMN = "target_load_mw"

MIN_ORIGIN_POSITION = 336  # 2 full weeks -- covers lag_168/lag_336 for any horizon <= 72h


def _renewable_cf_profile(full_history: pd.DataFrame) -> dict[tuple[int, int], float]:
    combined_cf = full_history["renewable_actual_mw"] / (
        full_history["solar_capacity_mw"] + full_history["wind_capacity_mw"]
    )
    profile = combined_cf.groupby([combined_cf.index.month, combined_cf.index.hour]).median()
    return {(int(m), int(h)): float(v) for (m, h), v in profile.items()}


def build_feature_rows(
    full_history: pd.DataFrame,
    horizons: list[int],
    origin_stride: int = 1,
) -> pd.DataFrame:
    """Build one row per (origin, horizon) pair, vectorized per horizon.

    `origin_stride` subsamples origin timestamps (e.g. 6 = every 6th hour)
    to control training-set size without biasing which horizons are covered.
    """
    idx = full_history.index
    n = len(full_history)
    load = full_history["load_actual_mw"].to_numpy(dtype=float)

    load_series = pd.Series(load)
    roll_mean_24 = load_series.rolling(24, min_periods=24).mean().to_numpy()
    roll_mean_168 = load_series.rolling(168, min_periods=168).mean().to_numpy()
    roll_std_168 = load_series.rolling(168, min_periods=168).std().to_numpy()

    seasonal = full_history["load_actual_mw"].groupby(
        [full_history.index.dayofweek, full_history.index.hour]
    ).median()
    seasonal_lookup = np.array(
        [float(seasonal.get((ts.dayofweek, ts.hour), np.nan)) for ts in idx]
    )

    solar_cap = full_history["solar_capacity_mw"].to_numpy(dtype=float)
    wind_cap = full_history["wind_capacity_mw"].to_numpy(dtype=float)
    total_capacity = solar_cap + wind_cap
    cf_profile = _renewable_cf_profile(full_history)

    max_origin = n - 1 - max(horizons)
    origin_positions = np.arange(MIN_ORIGIN_POSITION, max_origin + 1, origin_stride)

    frames = []
    for h in horizons:
        origin_idx = origin_positions
        target_idx = origin_idx + h
        lag168_idx = target_idx - 168
        lag336_idx = target_idx - 336
        valid = (lag336_idx >= 0) & (target_idx < n)
        origin_idx = origin_idx[valid]
        target_idx = target_idx[valid]
        lag168_idx = lag168_idx[valid]
        lag336_idx = lag336_idx[valid]

        target_ts = idx[target_idx]
        trend_ratio = roll_mean_168[origin_idx] / np.where(
            seasonal_lookup[origin_idx] > 0, seasonal_lookup[origin_idx], np.nan
        )

        renewable_cf_expected = np.array(
            [cf_profile.get((ts.month, ts.hour), np.nan) for ts in target_ts]
        )

        hour = target_ts.hour.to_numpy()
        dow = target_ts.dayofweek.to_numpy()
        month = target_ts.month.to_numpy()

        frame = pd.DataFrame(
            {
                "origin_ts": idx[origin_idx],
                "horizon_h": h,
                "target_ts": target_ts,
                "roll_mean_24": roll_mean_24[origin_idx],
                "roll_mean_168": roll_mean_168[origin_idx],
                "roll_std_168": roll_std_168[origin_idx],
                "lag_168": load[lag168_idx],
                "lag_336": load[lag336_idx],
                "trend_ratio": trend_ratio,
                "renewable_cf_expected": renewable_cf_expected * total_capacity[origin_idx],
                "hour_sin": np.sin(2 * np.pi * hour / 24),
                "hour_cos": np.cos(2 * np.pi * hour / 24),
                "dow_sin": np.sin(2 * np.pi * dow / 7),
                "dow_cos": np.cos(2 * np.pi * dow / 7),
                "month_sin": np.sin(2 * np.pi * month / 12),
                "month_cos": np.cos(2 * np.pi * month / 12),
                "is_weekend": (dow >= 5).astype(float),
                TARGET_COLUMN: load[target_idx],
            }
        )
        frames.append(frame)

    rows = pd.concat(frames, ignore_index=True)
    rows = rows.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN])
    return rows


def build_inference_features(
    history: pd.DataFrame,
    full_history: pd.DataFrame,
    horizons: list[int],
) -> pd.DataFrame:
    """Same feature logic as `build_feature_rows`, but for a single live origin
    (the last timestamp in `history`) predicting forward `horizons` hours --
    used at request time, not during training.
    """
    origin_ts = history.index.max()
    origin_pos = full_history.index.get_loc(origin_ts)
    if isinstance(origin_pos, slice):
        origin_pos = origin_pos.stop - 1

    window = full_history.iloc[: origin_pos + 1]
    load = window["load_actual_mw"]
    roll_mean_24 = float(load.iloc[-24:].mean())
    roll_mean_168 = float(load.iloc[-168:].mean())
    roll_std_168 = float(load.iloc[-168:].std())

    seasonal = full_history["load_actual_mw"].groupby(
        [full_history.index.dayofweek, full_history.index.hour]
    ).median()
    seasonal_at_origin = float(seasonal.get((origin_ts.dayofweek, origin_ts.hour), load.mean()))
    trend_ratio = roll_mean_168 / seasonal_at_origin if seasonal_at_origin > 0 else 1.0

    total_capacity = float(
        full_history["solar_capacity_mw"].iloc[origin_pos] + full_history["wind_capacity_mw"].iloc[origin_pos]
    )
    cf_profile = _renewable_cf_profile(full_history)

    full_load = full_history["load_actual_mw"].to_numpy(dtype=float)

    rows = []
    for h in horizons:
        target_ts = origin_ts + pd.Timedelta(hours=h)
        target_pos = origin_pos + h
        lag168_pos = target_pos - 168
        lag336_pos = target_pos - 336
        lag_168 = float(full_load[lag168_pos]) if lag168_pos >= 0 else float(load.iloc[-1])
        lag_336 = float(full_load[lag336_pos]) if lag336_pos >= 0 else lag_168
        renewable_cf_expected = cf_profile.get((target_ts.month, target_ts.hour), 0.0) * total_capacity

        hour, dow, month = target_ts.hour, target_ts.dayofweek, target_ts.month
        rows.append(
            {
                "horizon_h": h,
                "target_ts": target_ts,
                "roll_mean_24": roll_mean_24,
                "roll_mean_168": roll_mean_168,
                "roll_std_168": roll_std_168,
                "lag_168": lag_168,
                "lag_336": lag_336,
                "trend_ratio": trend_ratio,
                "renewable_cf_expected": renewable_cf_expected,
                "hour_sin": np.sin(2 * np.pi * hour / 24),
                "hour_cos": np.cos(2 * np.pi * hour / 24),
                "dow_sin": np.sin(2 * np.pi * dow / 7),
                "dow_cos": np.cos(2 * np.pi * dow / 7),
                "month_sin": np.sin(2 * np.pi * month / 12),
                "month_cos": np.cos(2 * np.pi * month / 12),
                "is_weekend": float(dow >= 5),
            }
        )

    return pd.DataFrame(rows)
