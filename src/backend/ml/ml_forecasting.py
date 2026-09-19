"""Inference wrapper for the trained demand-forecasting model.

Produces the exact same `ForecastResult`/`HourlyForecast` shape as the
deterministic seasonal-naive forecaster in `backend/tools/forecasting.py`,
so it's a drop-in alternative everywhere downstream (load-balancing,
curtailment, facts, narration, verification) without any other code
needing to change.

`baseline_mw` / `baseline_std_mw` (used only for spike detection -- "is
this forecast hour unusual versus the normal weekly pattern") still come
from the same seasonal profile the deterministic model uses; only
`forecast_mw` itself (and the bounds built around it) comes from the
trained model. This keeps spike semantics identical while upgrading
forecast accuracy.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from backend.ml.features import FEATURE_COLUMNS, build_inference_features
from backend.tools.forecasting import (
    DEFAULT_LOOKBACK_WEEKS,
    DEFAULT_SPIKE_STD_THRESHOLD,
    ForecastResult,
    HourlyForecast,
    _seasonal_profile,
)

MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "models"
MODEL_PATH = MODEL_DIR / "demand_forecast_hgb.joblib"
METADATA_PATH = MODEL_DIR / "demand_forecast_hgb.metadata.json"


class ModelNotTrainedError(RuntimeError):
    """Raised when the ML forecaster is requested but no trained artifact exists."""


@lru_cache(maxsize=1)
def _load_model_and_metadata():
    if not MODEL_PATH.exists() or not METADATA_PATH.exists():
        raise ModelNotTrainedError(
            f"No trained model found at {MODEL_PATH}. Run "
            "`python -m backend.ml.train_demand_model` from src/ first."
        )
    model = joblib.load(MODEL_PATH)
    metadata = json.loads(METADATA_PATH.read_text())
    return model, metadata


def is_model_available() -> bool:
    return MODEL_PATH.exists() and METADATA_PATH.exists()


def ml_forecast_demand(
    history: pd.DataFrame,
    full_history: pd.DataFrame,
    horizon_hours: int = 24,
    lookback_weeks: int = DEFAULT_LOOKBACK_WEEKS,
    spike_std_threshold: float = DEFAULT_SPIKE_STD_THRESHOLD,
) -> ForecastResult:
    model, metadata = _load_model_and_metadata()
    residual_std_by_horizon = metadata["residual_std_by_horizon_mw"]

    horizons = list(range(1, horizon_hours + 1))
    features = build_inference_features(history, full_history, horizons)
    predictions = model.predict(features[FEATURE_COLUMNS])

    profile = _seasonal_profile(history["load_actual_mw"], lookback_weeks)

    hourly: list[HourlyForecast] = []
    for (_, row), forecast_mw in zip(features.iterrows(), predictions):
        ts = row["target_ts"]
        key = (ts.dayofweek, ts.hour)
        if key in profile.index:
            baseline = float(profile.loc[key, "median_mw"])
            baseline_std = float(profile.loc[key, "std_mw"])
        else:
            baseline = float(history["load_actual_mw"].mean())
            baseline_std = float(history["load_actual_mw"].std())

        forecast_mw = float(forecast_mw)
        # data-driven residual std for this specific horizon (from held-out
        # test-set errors at training time), falling back to the nearest
        # trained horizon if this exact one wasn't in the training grid.
        h = int(row["horizon_h"])
        band_std = residual_std_by_horizon.get(str(h))
        if band_std is None:
            nearest = min((int(k) for k in residual_std_by_horizon), key=lambda k: abs(k - h))
            band_std = residual_std_by_horizon[str(nearest)]

        upper = forecast_mw + 1.96 * band_std
        lower = max(0.0, forecast_mw - 1.96 * band_std)
        severity = (forecast_mw - baseline) / baseline_std if baseline_std > 0 else 0.0

        hourly.append(
            HourlyForecast(
                timestamp=ts,
                forecast_mw=round(forecast_mw, 1),
                baseline_mw=round(baseline, 1),
                baseline_std_mw=round(baseline_std, 1),
                upper_bound_mw=round(upper, 1),
                lower_bound_mw=round(lower, 1),
                is_spike=bool(severity > spike_std_threshold),
                spike_severity_std=round(float(severity), 2),
            )
        )

    return ForecastResult(
        hourly=hourly,
        trend_factor=1.0,  # not used by the ML path; kept for schema compatibility
        lookback_weeks=lookback_weeks,
        spike_std_threshold=spike_std_threshold,
    )
