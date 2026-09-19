"""Fact ledger: wraps already-computed pipeline outputs in provenance-tagged facts.

GridSentinel spec ss10: "The operator brief must never be the primary computation
layer. First compute structured facts; only then generate prose." This module
never computes a number itself -- it only takes numbers that already exist in the
pipeline state (forecast, anomalies, load balance, curtailment) and gives each one
a fact_id, unit, time window and a plain-English description of the calculation
that produced it, so any figure shown to an operator can be traced back to its
inputs via `GET /api/runs/{run_id}/facts/{fact_id}`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Fact:
    fact_id: str
    metric: str
    value: Any
    unit: str
    calculation: str
    time_window: dict[str, str | None] = field(default_factory=dict)
    entity_scope: list[str] = field(default_factory=list)


def _iso(value) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else value


def build_fact_ledger(state: dict, run_id: str) -> list[Fact]:
    facts: list[Fact] = []
    counter = 0

    def add(metric: str, value, unit: str, calculation: str, start=None, end=None, entity_scope=None) -> None:
        nonlocal counter
        counter += 1
        facts.append(
            Fact(
                fact_id=f"{run_id}_f{counter}",
                metric=metric,
                value=round(float(value), 3) if isinstance(value, (int, float)) else value,
                unit=unit,
                calculation=calculation,
                time_window={"start": _iso(start), "end": _iso(end)},
                entity_scope=entity_scope or ["grid_zone"],
            )
        )

    forecast = state.get("forecast")
    if forecast and forecast.peak:
        add(
            "peak_demand_forecast_mw",
            forecast.peak.forecast_mw,
            "MW",
            "Seasonal-naive median load for this weekday/hour over the lookback window, "
            "scaled by the trailing 7-day trend factor.",
            start=forecast.peak.timestamp,
            end=forecast.peak.timestamp,
        )
        add(
            "demand_spike_count",
            len(forecast.spikes),
            "count",
            f"Forecast hours exceeding the seasonal baseline by more than "
            f"{forecast.spike_std_threshold} standard deviations.",
        )

    backtest = state.get("forecast_backtest")
    if backtest and backtest.n_points:
        add(
            "forecast_mae_mw",
            backtest.mae,
            "MW",
            f"Rolling-origin backtest mean absolute error over {backtest.n_folds} fold(s), "
            f"{backtest.n_points} forecast-vs-actual point(s).",
        )
        add(
            "forecast_improvement_vs_naive_pct",
            backtest.improvement_pct,
            "%",
            "MAE improvement of the seasonal-trend model over a same-hour-last-week naive baseline, "
            "measured over the same backtest folds.",
        )

    for finding in state.get("anomalies", []):
        ep = finding.episode
        add(
            f"{ep.asset}_anomaly_avg_deviation_pct",
            ep.avg_deviation * 100,
            "%",
            f"Average (actual - expected) capacity factor over the {ep.direction}performance "
            f"episode. Root cause: {finding.label} (confidence {finding.confidence:.0%}).",
            start=ep.start,
            end=ep.end,
            entity_scope=[ep.asset],
        )

    load_balance = state.get("load_balance")
    if load_balance and load_balance.feasible:
        add(
            "load_balance_total_cost",
            load_balance.total_cost,
            "USD",
            "Sum of the load-balancing LP objective (dispatch + storage cycling + shed + "
            "curtailment + unmet-demand penalties) over the horizon.",
        )
        add(
            "load_balance_unmet_demand_mwh",
            load_balance.total_unmet_mwh,
            "MWh",
            "Demand that dispatchable capacity, storage and demand-response could not cover "
            "within their configured limits.",
        )

    curtailment = state.get("curtailment")
    if curtailment:
        add(
            "curtailment_avoided_mwh",
            curtailment.curtailment_avoided_mwh,
            "MWh",
            "baseline_curtailed_mwh - optimized_curtailed_mwh, where both plans are solved by "
            "the same load-balancing LP over the same forecast; baseline has no storage or "
            "demand response, optimized has the full configured flexibility.",
        )
        add(
            "curtailment_reduction_pct",
            curtailment.curtailment_reduction_pct,
            "%",
            "curtailment_avoided_mwh / baseline_curtailed_mwh.",
        )

    regional = state.get("regional_distribution")
    if regional:
        add(
            "regional_demand_fulfillment_pct",
            regional.overall_fulfillment_pct,
            "%",
            "Population-weighted per-region share of peak forecast demand, routed from the "
            "least-cost combination of generation hubs subject to each hub's capacity; "
            "% of total demand actually covered.",
        )
        add(
            "regional_unmet_demand_mw",
            regional.total_unmet_mw,
            "MW",
            "Sum of per-region shortfall after least-cost routing -- demand that could not be "
            "covered by any generation hub's remaining capacity.",
        )
        add(
            "regional_transmission_cost_usd",
            regional.total_transmission_cost_usd,
            "USD",
            "Sum of (distance_km x illustrative $/MW/km rate x MW delivered) over every "
            "hub-to-region route used in the least-cost allocation.",
        )

    return facts


def facts_by_id(facts: list[Fact]) -> dict[str, Fact]:
    return {f.fact_id: f for f in facts}
