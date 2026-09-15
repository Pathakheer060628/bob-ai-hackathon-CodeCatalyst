"""Verifier agent: catches narrated numbers that don't trace back to computed state.

Every MW/MWh/% figure the narrator writes into the brief must correspond
(within a small numeric tolerance, for rounding) to a number that actually
exists in the computed GridState -- the forecast, the anomaly episodes, the
load-balancing plan, or the curtailment plan. The verifier re-extracts every
number from the generated prose with a regex, builds the set of all
"trusted" numbers from state, and flags anything in the prose that isn't
close to any of them.

This is what makes it defensible to hand a generated brief to a grid
operator: the narrator (whether the offline template or a real LLM call via
the Bob/watsonx provider) can rephrase and reorganize, but it cannot
introduce a number that the deterministic tools didn't actually compute.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?(?:\sUTC)?")
# Negative lookbehind on the leading "-" stops range dashes like "43998-52002" from
# being read as a negative fifty-two-thousand -- only a "-" not glued to a preceding
# digit (i.e. a real minus sign) is captured.
NUMBER_PATTERN = re.compile(r"(?<!\d)-?\d[\d,]*\.?\d*")
RELATIVE_TOLERANCE = 0.01  # 1% -- accommodates rounding/formatting differences


@dataclass
class VerificationResult:
    trusted: bool
    checked_numbers: list[float] = field(default_factory=list)
    unverified_numbers: list[float] = field(default_factory=list)
    trusted_pool_size: int = 0


def _extract_numbers(text: str) -> list[float]:
    text = TIMESTAMP_PATTERN.sub(" ", text)
    numbers = []
    for match in NUMBER_PATTERN.finditer(text):
        cleaned = match.group().replace(",", "")
        try:
            value = float(cleaned)
        except ValueError:
            continue
        numbers.append(value)
    return numbers


def _collect_trusted_numbers(state: dict) -> set[float]:
    trusted: set[float] = set()

    def add(value) -> None:
        if isinstance(value, (int, float)):
            trusted.add(round(float(value), 2))
            trusted.add(round(float(value)))  # also allow whole-number rendering

    forecast = state.get("forecast")
    if forecast:
        for h in forecast.hourly:
            for v in (h.forecast_mw, h.baseline_mw, h.upper_bound_mw, h.lower_bound_mw, h.spike_severity_std):
                add(v)
        add(forecast.trend_factor)
        add(forecast.lookback_weeks)
        add(forecast.spike_std_threshold)
        add(len(forecast.hourly))
        add(len(forecast.spikes))

    for finding in state.get("anomalies", []):
        ep = finding.episode
        add(ep.duration_hours)
        add(ep.avg_deviation * 100)  # narrated as a percentage
        add(ep.avg_deviation)
        add(ep.peak_deviation)

    plan = state.get("load_balance")
    if plan and plan.feasible:
        add(plan.total_cost)
        add(plan.total_curtailed_mwh)
        add(plan.total_shed_mwh)
        add(plan.total_unmet_mwh)
        add(len(plan.actions_needed))

    curtailment = state.get("curtailment")
    if curtailment:
        add(curtailment.baseline_curtailed_mwh)
        add(curtailment.optimized_curtailed_mwh)
        add(curtailment.curtailment_avoided_mwh)
        add(curtailment.curtailment_reduction_pct)

    return trusted


def _is_trusted(number: float, trusted: set[float]) -> bool:
    if round(number, 2) in trusted or round(number) in trusted:
        return True
    for t in trusted:
        if t == 0:
            continue
        if abs(number - t) <= RELATIVE_TOLERANCE * abs(t):
            return True
    return False


def verify_brief(narrative_text: str, state: dict) -> VerificationResult:
    trusted = _collect_trusted_numbers(state)
    candidates = _extract_numbers(narrative_text)

    checked, unverified = [], []
    for n in candidates:
        # skip small integers that are almost certainly prose artefacts (list
        # markers, "1 hour", years in timestamps) rather than reported metrics
        if n == int(n) and 0 <= n <= 24 and n in trusted:
            checked.append(n)
            continue
        if _is_trusted(n, trusted):
            checked.append(n)
        else:
            unverified.append(n)

    return VerificationResult(
        trusted=len(unverified) == 0,
        checked_numbers=checked,
        unverified_numbers=unverified,
        trusted_pool_size=len(trusted),
    )
