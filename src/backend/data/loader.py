"""Loads the real German grid dataset and exposes it as a cached DataFrame."""

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).parent / "grid_renewable_de_2017_2019.csv"


@lru_cache(maxsize=1)
def load_grid_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp_utc"])
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df = df.set_index("timestamp_utc").sort_index()

    df["solar_capacity_factor"] = (df["solar_actual_mw"] / df["solar_capacity_mw"]).clip(0, 1)
    df["wind_capacity_factor"] = (df["wind_actual_mw"] / df["wind_capacity_mw"]).clip(0, 1)
    df["wind_onshore_capacity_factor"] = (
        df["wind_onshore_actual_mw"] / df["wind_onshore_capacity_mw"]
    ).clip(0, 1)
    df["wind_offshore_capacity_factor"] = (
        df["wind_offshore_actual_mw"] / df["wind_offshore_capacity_mw"]
    ).clip(0, 1)
    df["renewable_actual_mw"] = df["solar_actual_mw"] + df["wind_actual_mw"]
    df["load_forecast_error_mw"] = df["load_actual_mw"] - df["load_forecast_mw"]

    return df


def data_bounds() -> tuple[datetime, datetime]:
    df = load_grid_data()
    return df.index.min().to_pydatetime(), df.index.max().to_pydatetime()


def get_window(start: datetime, end: datetime) -> pd.DataFrame:
    df = load_grid_data()
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    window = df.loc[start:end]
    if window.empty:
        raise ValueError(f"No data in range {start} .. {end}. Dataset spans {data_bounds()}.")
    return window
