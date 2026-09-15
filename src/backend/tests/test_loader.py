from datetime import datetime, timezone

import pytest

from backend.data.loader import DATA_PATH, data_bounds, get_window, load_grid_data


def test_load_grid_data_has_expected_columns():
    df = load_grid_data()
    for col in ["load_actual_mw", "solar_actual_mw", "wind_actual_mw", "renewable_actual_mw"]:
        assert col in df.columns
    assert df.index.is_monotonic_increasing
    assert not df.isna().any().any()


def test_data_bounds_within_2017_2019():
    start, end = data_bounds()
    assert start.year == 2017
    assert end.year <= 2020


def test_get_window_returns_slice_within_bounds():
    start, _ = data_bounds()
    window = get_window(start, start)
    assert len(window) >= 1


def test_get_window_out_of_range_raises():
    with pytest.raises(ValueError):
        get_window(datetime(2050, 1, 1, tzinfo=timezone.utc), datetime(2050, 1, 2, tzinfo=timezone.utc))


def test_dataset_csv_exists_at_expected_location():
    assert DATA_PATH.exists()
    assert DATA_PATH.suffix == ".csv"
    assert DATA_PATH.stat().st_size > 0


def test_load_grid_data_is_cached_and_consistent_across_calls():
    df1 = load_grid_data()
    df2 = load_grid_data()
    # lru_cache(maxsize=1) means repeated calls return the exact same object,
    # not just equal data -- verifies the cache is actually being hit.
    assert df1 is df2
    assert len(df1) == len(df2)
    assert df1.index.equals(df2.index)
