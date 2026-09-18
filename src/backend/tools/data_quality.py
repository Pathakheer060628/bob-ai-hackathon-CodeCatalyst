"""Data-quality gate: pre-flight checks on a requested run window.

Runs before forecasting/optimization touch the data at all. Computes a
completeness score, flags gaps/duplicates/physically-impossible readings, and
decides whether the window is fit to forecast over. A hard failure here
blocks the run from proceeding to optimization (GridSentinel spec ss4.3,
ss20: "A new run cannot proceed to optimization when required data fails
hard quality checks") rather than letting a downstream tool fail on bad
input or, worse, silently produce a plausible-looking but ungrounded result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

MIN_REQUIRED_HOURS = 24 * 7  # one full week -- needed for the seasonal forecast profile
HARD_FAIL_COMPLETENESS = 0.85
WARN_COMPLETENESS = 0.98
WARN_MAX_GAP_HOURS = 3


@dataclass
class DataQualityReport:
    expected_hours: int
    actual_hours: int
    completeness_score: float
    duplicate_count: int
    max_gap_hours: int
    negative_load_hours: int
    negative_generation_hours: int
    warnings: list[str] = field(default_factory=list)
    hard_fail: bool = False
    hard_fail_reasons: list[str] = field(default_factory=list)


def assess_window_quality(
    window: pd.DataFrame, min_required_hours: int = MIN_REQUIRED_HOURS
) -> DataQualityReport:
    if window.empty:
        return DataQualityReport(
            expected_hours=min_required_hours,
            actual_hours=0,
            completeness_score=0.0,
            duplicate_count=0,
            max_gap_hours=0,
            negative_load_hours=0,
            negative_generation_hours=0,
            hard_fail=True,
            hard_fail_reasons=["Window contains no rows."],
        )

    index = window.index
    expected_hours = int(round((index.max() - index.min()) / pd.Timedelta(hours=1))) + 1
    actual_hours = len(index)
    completeness_score = round(actual_hours / expected_hours, 4) if expected_hours > 0 else 0.0

    duplicate_count = int(index.duplicated().sum())

    gaps = index.to_series().diff().dropna()
    max_gap_hours = int(gaps.max() / pd.Timedelta(hours=1)) if not gaps.empty else 0

    negative_load_hours = int((window["load_actual_mw"] < 0).sum()) if "load_actual_mw" in window else 0
    negative_generation_hours = int(
        (window.get("solar_actual_mw", 0) < 0).sum() + (window.get("wind_actual_mw", 0) < 0).sum()
    )

    warnings: list[str] = []
    hard_fail_reasons: list[str] = []

    if actual_hours < min_required_hours:
        hard_fail_reasons.append(
            f"Only {actual_hours} hourly points available; at least {min_required_hours} "
            "(one week) are required to build a seasonal forecast baseline."
        )
    if completeness_score < HARD_FAIL_COMPLETENESS:
        hard_fail_reasons.append(
            f"Timestamp completeness {completeness_score:.0%} is below the "
            f"{HARD_FAIL_COMPLETENESS:.0%} minimum -- too many missing hours in this window."
        )
    elif completeness_score < WARN_COMPLETENESS:
        warnings.append(f"Timestamp completeness {completeness_score:.0%}: minor gaps present.")

    if duplicate_count > 0:
        hard_fail_reasons.append(f"{duplicate_count} duplicate timestamp(s) found in this window.")

    if max_gap_hours > WARN_MAX_GAP_HOURS:
        warnings.append(f"Largest single gap in the window is {max_gap_hours}h.")

    if negative_load_hours:
        warnings.append(f"{negative_load_hours} hour(s) with negative load reading (physically impossible).")
    if negative_generation_hours:
        warnings.append(f"{negative_generation_hours} hour(s) with negative generation reading.")

    return DataQualityReport(
        expected_hours=expected_hours,
        actual_hours=actual_hours,
        completeness_score=completeness_score,
        duplicate_count=duplicate_count,
        max_gap_hours=max_gap_hours,
        negative_load_hours=negative_load_hours,
        negative_generation_hours=negative_generation_hours,
        warnings=warnings,
        hard_fail=len(hard_fail_reasons) > 0,
        hard_fail_reasons=hard_fail_reasons,
    )
