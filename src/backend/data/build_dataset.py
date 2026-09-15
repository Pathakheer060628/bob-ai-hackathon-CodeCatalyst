"""Regenerates grid_renewable_de_2017_2019.csv from the raw OPSD time series file.

Not run automatically -- the derived CSV is already committed. This script
documents exactly how it was produced from the raw ~124MB OPSD download, per
DATA_SOURCE.md.
"""

from pathlib import Path

import pandas as pd

RAW_URL = (
    "https://data.open-power-system-data.org/time_series/2020-10-06/"
    "time_series_60min_singleindex.csv"
)

COLUMNS = [
    "utc_timestamp",
    "DE_load_actual_entsoe_transparency",
    "DE_load_forecast_entsoe_transparency",
    "DE_solar_capacity",
    "DE_solar_generation_actual",
    "DE_wind_capacity",
    "DE_wind_generation_actual",
    "DE_wind_offshore_capacity",
    "DE_wind_offshore_generation_actual",
    "DE_wind_onshore_capacity",
    "DE_wind_onshore_generation_actual",
]

RENAME = {
    "utc_timestamp": "timestamp_utc",
    "DE_load_actual_entsoe_transparency": "load_actual_mw",
    "DE_load_forecast_entsoe_transparency": "load_forecast_mw",
    "DE_solar_capacity": "solar_capacity_mw",
    "DE_solar_generation_actual": "solar_actual_mw",
    "DE_wind_capacity": "wind_capacity_mw",
    "DE_wind_generation_actual": "wind_actual_mw",
    "DE_wind_offshore_capacity": "wind_offshore_capacity_mw",
    "DE_wind_offshore_generation_actual": "wind_offshore_actual_mw",
    "DE_wind_onshore_capacity": "wind_onshore_capacity_mw",
    "DE_wind_onshore_generation_actual": "wind_onshore_actual_mw",
}

CAPACITY_COLUMNS = [
    "solar_capacity_mw",
    "wind_capacity_mw",
    "wind_offshore_capacity_mw",
    "wind_onshore_capacity_mw",
]


def build(raw_csv_path: str, out_path: str, start: str = "2017-01-01", end: str = "2020-01-01") -> None:
    df = pd.read_csv(raw_csv_path, usecols=COLUMNS, parse_dates=["utc_timestamp"])
    df = df[(df["utc_timestamp"] >= start) & (df["utc_timestamp"] < end)].reset_index(drop=True)
    df = df.rename(columns=RENAME)
    df[CAPACITY_COLUMNS] = df[CAPACITY_COLUMNS].ffill().bfill()
    df["load_forecast_mw"] = df["load_forecast_mw"].interpolate()
    df.to_csv(out_path, index=False)


if __name__ == "__main__":
    here = Path(__file__).parent
    build(str(here / "time_series_60min.csv"), str(here / "grid_renewable_de_2017_2019.csv"))
