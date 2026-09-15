# Data Source

`grid_renewable_de_2017_2019.csv` is a **real** dataset, not synthetic. It is a
derived subset of the [Open Power System Data](https://open-power-system-data.org/)
(OPSD) "Time series" package, version 2020-10-06:

> Open Power System Data. 2020. Data Package Time series.
> https://doi.org/10.25832/time_series/2020-10-06

OPSD aggregates and republishes real transmission-grid data reported by the
German TSOs (50Hertz, Amprion, TenneT, TransnetBW) to the
[ENTSO-E Transparency Platform](https://transparency.entsoe.eu/), under
**CC-BY 4.0**.

## What was extracted

From the full OPSD `time_series_60min_singleindex.csv` (all countries, 2015-2020,
~124 MB), we kept the national Germany (`DE_*`) columns and sliced to
2017-01-01 -- 2019-12-31 (3 full years, hourly resolution, 26,280 rows, zero
missing values after forward-filling slow-moving capacity fields):

| Column | Meaning |
|---|---|
| `timestamp_utc` | Hour timestamp, UTC |
| `load_actual_mw` | Actual German grid electricity demand (MW) |
| `load_forecast_mw` | TSO day-ahead load forecast (MW) |
| `solar_capacity_mw` | Installed solar capacity (MW) |
| `solar_actual_mw` | Actual solar generation (MW) |
| `wind_capacity_mw` | Installed total wind capacity (MW) |
| `wind_actual_mw` | Actual total wind generation (MW) |
| `wind_onshore_capacity_mw` / `wind_onshore_actual_mw` | Onshore wind capacity / actual generation |
| `wind_offshore_capacity_mw` / `wind_offshore_actual_mw` | Offshore wind capacity / actual generation |

This is real, historical grid operations data -- genuine demand spikes, genuine
renewable underperformance episodes, and genuine forecast-vs-actual gaps are
all present in it. Nothing here is fabricated or simulated.

## Regenerating it

```bash
curl -L -o time_series_60min.csv \
  https://data.open-power-system-data.org/time_series/2020-10-06/time_series_60min_singleindex.csv
python src/backend/data/build_dataset.py   # extracts + saves grid_renewable_de_2017_2019.csv
```
