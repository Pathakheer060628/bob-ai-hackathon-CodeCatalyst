"""Trains the demand-forecasting model on the real German grid dataset.

Model: sklearn.ensemble.HistGradientBoostingRegressor (gradient-boosted
decision trees, histogram-binned). Chosen over a neural net / deep learning
approach because:
  - The training set is ~26k hourly rows x a handful of features -- tabular,
    not sequence/image data at a scale where deep learning earns its cost.
  - Gradient-boosted trees are the standard, competition-proven choice for
    structured/tabular forecasting problems (this is the same family of
    model behind most Kaggle-winning tabular solutions).
  - It ships in scikit-learn, already a project dependency -- no new
    packages, no GPU, no extra install risk for judges re-running this.
  - It natively supports missing values and is robust to unscaled/mixed-
    magnitude features (MW rolling means next to sin/cos calendar terms),
    so no separate scaling pipeline is needed.
  - Native early stopping on a held-out validation split, and it exposes a
    permutation-importance-friendly `.predict()` for explainability -- the
    project's whole design principle (GridSentinel spec) is "every number
    traces back to something inspectable", and an opaque deep model would
    fight that.

Run:
    cd src
    python -m backend.ml.train_demand_model
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error

from backend.data.loader import load_grid_data
from backend.ml.features import FEATURE_COLUMNS, TARGET_COLUMN, build_feature_rows

MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "models"
MODEL_PATH = MODEL_DIR / "demand_forecast_hgb.joblib"
METADATA_PATH = MODEL_DIR / "demand_forecast_hgb.metadata.json"

HORIZONS = [1, 2, 3, 4, 6, 8, 12, 16, 20, 24, 30, 36, 42, 48, 54, 60, 66, 72]
TRAIN_TEST_SPLIT = "2019-01-01"  # train: 2017-01 .. 2018-12, test: all of 2019
ORIGIN_STRIDE = 3  # subsample origins every 3h to keep training-set size manageable

HYPERPARAMS = dict(
    loss="squared_error",
    learning_rate=0.06,
    max_iter=400,
    max_depth=7,
    max_leaf_nodes=31,
    min_samples_leaf=40,
    l2_regularization=0.1,
    early_stopping=True,
    validation_fraction=0.1,
    n_iter_no_change=20,
    random_state=42,
)


def _naive_baseline_mae(test_df: pd.DataFrame) -> float:
    # same-hour-last-week naive forecast == the lag_168 feature itself
    return float(mean_absolute_error(test_df[TARGET_COLUMN], test_df["lag_168"]))


def main() -> None:
    print("Loading full dataset...")
    full_history = load_grid_data()
    print(f"  {len(full_history)} hourly rows, {full_history.index.min()} .. {full_history.index.max()}")

    print(f"Building leakage-safe training rows for horizons {HORIZONS} (origin stride={ORIGIN_STRIDE}h)...")
    rows = build_feature_rows(full_history, horizons=HORIZONS, origin_stride=ORIGIN_STRIDE)
    print(f"  {len(rows)} (origin, horizon) training rows")

    split_ts = pd.Timestamp(TRAIN_TEST_SPLIT, tz=full_history.index.tz)
    train_df = rows[rows["origin_ts"] < split_ts]
    test_df = rows[rows["origin_ts"] >= split_ts]
    print(f"  train: {len(train_df)} rows (< {TRAIN_TEST_SPLIT}), test: {len(test_df)} rows (>= {TRAIN_TEST_SPLIT})")

    X_train, y_train = train_df[FEATURE_COLUMNS], train_df[TARGET_COLUMN]
    X_test, y_test = test_df[FEATURE_COLUMNS], test_df[TARGET_COLUMN]

    print(f"Training HistGradientBoostingRegressor: {HYPERPARAMS}")
    model = HistGradientBoostingRegressor(**HYPERPARAMS)
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
    mape = float(mean_absolute_percentage_error(y_test, pred) * 100)
    naive_mae = _naive_baseline_mae(test_df)
    improvement_pct = round((1 - mae / naive_mae) * 100, 2) if naive_mae > 0 else 0.0

    print(f"Test MAE: {mae:.1f} MW | RMSE: {rmse:.1f} MW | MAPE: {mape:.2f}%")
    print(f"Naive (same-hour-last-week) MAE: {naive_mae:.1f} MW")
    print(f"Improvement over naive: {improvement_pct:+.1f}%")

    print("Computing permutation feature importance (test sample)...")
    sample = X_test.sample(n=min(5000, len(X_test)), random_state=42)
    sample_y = y_test.loc[sample.index]
    importance = permutation_importance(
        model, sample, sample_y, scoring="neg_mean_absolute_error", n_repeats=5, random_state=42, n_jobs=-1
    )
    ranked = sorted(
        zip(FEATURE_COLUMNS, importance.importances_mean.tolist()), key=lambda kv: kv[1], reverse=True
    )
    print("Feature importance (mean MAE increase in MW when shuffled), most -> least useful:")
    for name, score in ranked:
        print(f"  {name:24s} {score:8.1f}")

    # per-horizon residual std -> used at inference time to build a
    # data-driven confidence band around each forecast hour, instead of an
    # arbitrary constant.
    test_df = test_df.copy()
    test_df["abs_error"] = np.abs(pred - y_test.to_numpy())
    residual_std_by_horizon = {
        int(h): float(g["abs_error"].std() * 1.4826) if len(g) > 1 else float(g["abs_error"].mean())
        for h, g in test_df.groupby("horizon_h")
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_type": "sklearn.ensemble.HistGradientBoostingRegressor",
        "hyperparameters": HYPERPARAMS,
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "horizons_trained": HORIZONS,
        "train_test_split": TRAIN_TEST_SPLIT,
        "origin_stride_hours": ORIGIN_STRIDE,
        "n_train_rows": int(len(train_df)),
        "n_test_rows": int(len(test_df)),
        "data_window": {
            "start": full_history.index.min().isoformat(),
            "end": full_history.index.max().isoformat(),
        },
        "metrics": {
            "mae_mw": round(mae, 1),
            "rmse_mw": round(rmse, 1),
            "mape_pct": round(mape, 2),
            "naive_mae_mw": round(naive_mae, 1),
            "improvement_over_naive_pct": improvement_pct,
        },
        "feature_importance": [{"feature": n, "importance_mw": round(s, 2)} for n, s in ranked],
        "residual_std_by_horizon_mw": residual_std_by_horizon,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))

    print(f"\nSaved model -> {MODEL_PATH}")
    print(f"Saved metadata -> {METADATA_PATH}")


if __name__ == "__main__":
    main()
