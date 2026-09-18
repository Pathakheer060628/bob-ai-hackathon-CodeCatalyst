import numpy as np
import pandas as pd

from backend.tools.data_quality import assess_window_quality


def _clean_window(hours: int = 24 * 10) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=hours, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "load_actual_mw": np.full(hours, 40000.0),
            "solar_actual_mw": np.full(hours, 1000.0),
            "wind_actual_mw": np.full(hours, 2000.0),
        },
        index=idx,
    )


def test_clean_window_passes_with_no_warnings():
    report = assess_window_quality(_clean_window())
    assert report.hard_fail is False
    assert report.warnings == []
    assert report.completeness_score == 1.0


def test_short_window_hard_fails_insufficient_coverage():
    report = assess_window_quality(_clean_window(hours=24 * 3), min_required_hours=24 * 7)
    assert report.hard_fail is True
    assert any("one week" in r for r in report.hard_fail_reasons)


def test_gappy_window_hard_fails_below_completeness_floor():
    df = _clean_window(hours=24 * 10)
    keep = df.index[: int(len(df) * 0.5)]  # drop half -- well below the 85% floor
    report = assess_window_quality(df.loc[keep])
    assert report.hard_fail is True


def test_minor_gap_is_a_soft_warning_not_a_hard_fail():
    df = _clean_window(hours=24 * 10)
    dropped = df.drop(df.index[5:6])  # single missing hour out of 240
    report = assess_window_quality(dropped)
    assert report.hard_fail is False
    assert report.completeness_score < 1.0


def test_negative_load_is_flagged_as_warning():
    df = _clean_window()
    df.iloc[0, df.columns.get_loc("load_actual_mw")] = -100.0
    report = assess_window_quality(df)
    assert report.negative_load_hours == 1
    assert any("negative load" in w for w in report.warnings)


def test_empty_window_hard_fails():
    df = _clean_window().iloc[0:0]
    report = assess_window_quality(df)
    assert report.hard_fail is True
