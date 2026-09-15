from datetime import datetime, timezone

import pytest

from backend.data.loader import data_bounds, get_window, load_grid_data


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
