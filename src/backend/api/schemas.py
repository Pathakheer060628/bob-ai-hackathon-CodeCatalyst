"""Pydantic request models + plain-dict serializers for GridState results.

The dataclasses in backend/tools/* and backend/agents/* carry pandas
Timestamps and are not directly JSON-serializable; the `serialize_*`
functions here convert a completed GridState into plain, JSON-safe dicts for
the API responses and SSE payloads.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.tools.load_balancing import LoadBalanceConfig


class LoadBalanceConfigIn(BaseModel):
    dispatchable_capacity_mw: float | None = None
    storage_capacity_mwh: float | None = None
    storage_max_rate_mw: float | None = None
    storage_efficiency: float = 0.9
    storage_initial_soc_mwh: float | None = None
    max_demand_response_fraction: float = 0.05


class ScenarioConfigIn(BaseModel):
    """What-if scenario (GridSentinel spec ss7): scales the forecast to demonstrate
    oversupply/curtailment value even when the underlying historical window is calm."""

    renewable_scale: float = Field(1.0, ge=0.1, le=5.0)
    demand_scale: float = Field(1.0, ge=0.3, le=3.0)
    label: str | None = None


class RunCreateRequest(BaseModel):
    window_end: str = Field(..., description="ISO timestamp: the 'as-of-now' point for the run")
    lookback_days: int = Field(30, ge=7, le=365)
    horizon_hours: int = Field(24, ge=1, le=72)
    load_balance_config: LoadBalanceConfigIn | None = None
    scenario: ScenarioConfigIn | None = None
    forecast_model: str = Field("seasonal", pattern="^(seasonal|ml)$")


def to_load_balance_config(payload: LoadBalanceConfigIn | None, peak_load_mw: float) -> LoadBalanceConfig | None:
    if payload is None:
        return None  # signals the orchestrator to compute its own default from history

    return LoadBalanceConfig(
        dispatchable_capacity_mw=payload.dispatchable_capacity_mw or round(peak_load_mw * 0.9, -2),
        storage_capacity_mwh=payload.storage_capacity_mwh or round(peak_load_mw * 0.08, -2),
        storage_max_rate_mw=payload.storage_max_rate_mw or round(peak_load_mw * 0.04, -2),
        storage_efficiency=payload.storage_efficiency,
        storage_initial_soc_mwh=payload.storage_initial_soc_mwh or round(peak_load_mw * 0.04, -2),
        max_demand_response_fraction=payload.max_demand_response_fraction,
    )


def serialize_forecast(forecast) -> dict[str, Any]:
    return {
        "trend_factor": forecast.trend_factor,
        "lookback_weeks": forecast.lookback_weeks,
        "spike_std_threshold": forecast.spike_std_threshold,
        "peak": _serialize_hourly_forecast(forecast.peak) if forecast.peak else None,
        "spike_count": len(forecast.spikes),
        "hourly": [_serialize_hourly_forecast(h) for h in forecast.hourly],
    }


def _serialize_hourly_forecast(h) -> dict[str, Any]:
    return {
        "timestamp": h.timestamp.isoformat(),
        "forecast_mw": h.forecast_mw,
        "baseline_mw": h.baseline_mw,
        "upper_bound_mw": h.upper_bound_mw,
        "lower_bound_mw": h.lower_bound_mw,
        "is_spike": h.is_spike,
        "spike_severity_std": h.spike_severity_std,
    }


def serialize_anomalies(findings) -> list[dict[str, Any]]:
    out = []
    for f in findings:
        ep = f.episode
        out.append(
            {
                "asset": ep.asset,
                "start": ep.start.isoformat(),
                "end": ep.end.isoformat(),
                "direction": ep.direction,
                "duration_hours": ep.duration_hours,
                "avg_deviation": ep.avg_deviation,
                "peak_deviation": ep.peak_deviation,
                "category": f.category,
                "label": f.label,
                "evidence": f.evidence,
                "confidence": f.confidence,
                "estimated_cost_usd": f.estimated_cost_usd,
                "cost_basis": f.cost_basis,
                "recommended_action": f.recommended_action,
            }
        )
    return out


def serialize_data_quality(report) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "expected_hours": report.expected_hours,
        "actual_hours": report.actual_hours,
        "completeness_score": report.completeness_score,
        "duplicate_count": report.duplicate_count,
        "max_gap_hours": report.max_gap_hours,
        "negative_load_hours": report.negative_load_hours,
        "negative_generation_hours": report.negative_generation_hours,
        "warnings": report.warnings,
        "hard_fail": report.hard_fail,
        "hard_fail_reasons": report.hard_fail_reasons,
    }


def serialize_backtest(backtest) -> dict[str, Any] | None:
    if backtest is None:
        return None
    return {
        "mae": backtest.mae,
        "rmse": backtest.rmse,
        "mape": backtest.mape,
        "naive_mae": backtest.naive_mae,
        "improvement_pct": backtest.improvement_pct,
        "n_points": backtest.n_points,
        "n_folds": backtest.n_folds,
        "horizon_hours": backtest.horizon_hours,
    }


def serialize_facts(facts) -> list[dict[str, Any]]:
    return [
        {
            "fact_id": f.fact_id,
            "metric": f.metric,
            "value": f.value,
            "unit": f.unit,
            "calculation": f.calculation,
            "time_window": f.time_window,
            "entity_scope": f.entity_scope,
        }
        for f in facts or []
    ]


def serialize_load_balance(plan) -> dict[str, Any]:
    return {
        "feasible": plan.feasible,
        "total_cost": plan.total_cost,
        "total_curtailed_mwh": plan.total_curtailed_mwh,
        "total_shed_mwh": plan.total_shed_mwh,
        "total_unmet_mwh": plan.total_unmet_mwh,
        "hours": [
            {
                "hour_index": h.hour_index,
                "demand_mw": h.demand_mw,
                "renewable_mw": h.renewable_mw,
                "dispatch_mw": h.dispatch_mw,
                "charge_mw": h.charge_mw,
                "discharge_mw": h.discharge_mw,
                "shed_mw": h.shed_mw,
                "curtail_mw": h.curtail_mw,
                "soc_mwh": h.soc_mwh,
                "unmet_mw": h.unmet_mw,
            }
            for h in plan.hours
        ],
    }


def serialize_curtailment(plan) -> dict[str, Any]:
    baseline_cost = plan.baseline.total_cost if plan.baseline.feasible else None
    optimized_cost = plan.optimized.total_cost if plan.optimized.feasible else None
    net_savings = (
        round(baseline_cost - optimized_cost, 2) if baseline_cost is not None and optimized_cost is not None else None
    )
    return {
        "baseline_curtailed_mwh": plan.baseline_curtailed_mwh,
        "optimized_curtailed_mwh": plan.optimized_curtailed_mwh,
        "curtailment_avoided_mwh": plan.curtailment_avoided_mwh,
        "curtailment_reduction_pct": plan.curtailment_reduction_pct,
        "baseline_total_cost_usd": baseline_cost,
        "optimized_total_cost_usd": optimized_cost,
        "net_savings_usd": net_savings,
        "recommended_actions": [
            {
                "hour_index": a.hour_index,
                "charge_mw": a.charge_mw,
                "discharge_mw": a.discharge_mw,
                "shed_mw": a.shed_mw,
            }
            for a in plan.recommended_actions
        ],
    }


def serialize_regional_distribution(plan) -> dict[str, Any]:
    return {
        "total_demand_mw": plan.total_demand_mw,
        "total_allocated_mw": plan.total_allocated_mw,
        "total_unmet_mw": plan.total_unmet_mw,
        "overall_fulfillment_pct": plan.overall_fulfillment_pct,
        "total_transmission_cost_usd": plan.total_transmission_cost_usd,
        "total_station_capacity_mw": plan.total_station_capacity_mw,
        "feasible": plan.feasible,
        "system_recommendation": plan.system_recommendation,
        "regions": [
            {
                "region": r.region,
                "population": r.population,
                "demand_mw": r.demand_mw,
                "nearest_station": r.nearest_station,
                "nearest_station_distance_km": r.nearest_station_distance_km,
                "allocated_mw": r.allocated_mw,
                "unmet_mw": r.unmet_mw,
                "fulfillment_pct": r.fulfillment_pct,
                "transmission_cost_usd": r.transmission_cost_usd,
                "recommended_action": r.recommended_action,
            }
            for r in plan.regions
        ],
    }


def serialize_algorithm_comparison(comparisons) -> list[dict[str, Any]]:
    return [
        {
            "algorithm": c.algorithm,
            "label": c.label,
            "overall_fulfillment_pct": c.overall_fulfillment_pct,
            "total_unmet_mw": c.total_unmet_mw,
            "total_transmission_cost_usd": c.total_transmission_cost_usd,
            "worst_region_fulfillment_pct": c.worst_region_fulfillment_pct,
        }
        for c in comparisons or []
    ]


# Illustrative business-layer assumptions -- same spirit as the illustrative
# $/MWh dispatch costs in backend/tools/load_balancing.py: not a real tariff
# or a real O&M contract, but a defensible, documented stand-in so a full
# revenue-vs-cost P&L can be computed rather than asserted.
#
# WHOLESALE_PRICE_USD_PER_MWH: ~ the real 2019 German day-ahead wholesale
# average (~EUR 37-40/MWh -> ~USD 42-45/MWh) -- what a grid operator actually
# realizes per MWh delivered, not a retail/residential rate.
#
# MAINTENANCE_RATE_USD_PER_MW_YEAR: a blended operations & maintenance
# benchmark across the generation mix this app models (thermal, onshore/
# offshore wind, solar, storage), in the range public O&M benchmarks (e.g.
# NREL's Annual Technology Baseline) report for those technologies --
# roughly $15k-45k/MW-year depending on technology; $25k/MW-year is a
# reasonable blended midpoint, not any single real contract.
WHOLESALE_PRICE_USD_PER_MWH = 45.0
MAINTENANCE_RATE_USD_PER_MW_YEAR = 25_000.0
HOURS_PER_YEAR = 8760


def serialize_business_impact(curtailment, anomalies, load_balance, regional, horizon_hours) -> dict[str, Any]:
    """Full run-level P&L: what this run's dispatch plan earns (energy
    actually delivered x wholesale price) against everything it costs to run
    it (LP operating cost + prorated fleet maintenance + regional
    transmission cost) -- not a rigged number, a real formula that can show
    a loss if the inputs are bad enough (e.g. heavy unmet-demand penalties
    or a severe anomaly-driven cost run), which is the point: this run's
    financial viability should be an honest computed answer, not an assumed
    one.

    Maintenance is prorated for the horizon this run actually covers
    (`horizon_hours` out of a year), applied to the total generation-hub
    capacity from the regional-distribution reference data (backend/data/
    regions.py) -- the broadest infrastructure figure now in the pipeline.

    `optimization_value_usd` / `anomaly_cost_exposure_usd` are kept as
    separate, non-netted context (see their own docstrings below) since they
    cover different time windows than the horizon-level P&L above them.
    """
    feasible = curtailment.baseline.feasible and curtailment.optimized.feasible
    optimization_value = (
        round(curtailment.baseline.total_cost - curtailment.optimized.total_cost, 2) if feasible else 0.0
    )
    anomaly_cost_exposure = round(sum(f.estimated_cost_usd for f in anomalies or []), 2)

    mwh_served = (
        sum(max(0.0, h.demand_mw - h.unmet_mw) for h in load_balance.hours)
        if load_balance and load_balance.feasible
        else 0.0
    )
    revenue_usd = round(mwh_served * WHOLESALE_PRICE_USD_PER_MWH, 2)

    operating_cost_usd = round(load_balance.total_cost, 2) if load_balance and load_balance.feasible else 0.0
    transmission_cost_usd = round(regional.total_transmission_cost_usd, 2) if regional else 0.0
    total_capacity_mw = regional.total_station_capacity_mw if regional else 0.0
    maintenance_cost_usd = round(
        total_capacity_mw * MAINTENANCE_RATE_USD_PER_MW_YEAR * (horizon_hours / HOURS_PER_YEAR), 2
    )

    total_cost_usd = round(operating_cost_usd + maintenance_cost_usd + transmission_cost_usd, 2)
    net_profit_usd = round(revenue_usd - total_cost_usd, 2)
    profit_margin_pct = round((net_profit_usd / revenue_usd) * 100, 1) if revenue_usd > 0 else None

    if revenue_usd <= 0:
        verdict = "undetermined"
    elif net_profit_usd > 0:
        verdict = "profit"
    elif net_profit_usd == 0:
        verdict = "breakeven"
    else:
        verdict = "loss"

    return {
        "revenue_usd": revenue_usd,
        "mwh_served": round(mwh_served, 1),
        "operating_cost_usd": operating_cost_usd,
        "maintenance_cost_usd": maintenance_cost_usd,
        "transmission_cost_usd": transmission_cost_usd,
        "total_cost_usd": total_cost_usd,
        "net_profit_usd": net_profit_usd,
        "profit_margin_pct": profit_margin_pct,
        "verdict": verdict,
        "wholesale_price_usd_per_mwh": WHOLESALE_PRICE_USD_PER_MWH,
        "maintenance_rate_usd_per_mw_year": MAINTENANCE_RATE_USD_PER_MW_YEAR,
        "optimization_value_usd": optimization_value,
        "anomaly_cost_exposure_usd": anomaly_cost_exposure,
    }


def serialize_verification(result) -> dict[str, Any]:
    return {
        "trusted": result.trusted,
        "checked_count": len(result.checked_numbers),
        "unverified_numbers": result.unverified_numbers,
        "trusted_pool_size": result.trusted_pool_size,
    }


def serialize_run_summary(record: Any) -> dict[str, Any]:
    """Compact summary of a RunRecord for the run-list / command-center views.

    Pulls a handful of headline figures out of an already-computed result
    (never recomputes anything) so the frontend can render run cards without
    re-fetching the full result payload for every row.
    """
    summary: dict[str, Any] = {
        "run_id": record.run_id,
        "status": record.status,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "window_end": record.window_end,
        "lookback_days": record.lookback_days,
        "horizon_hours": record.horizon_hours,
        "error": record.error,
        "peak_demand_mw": None,
        "renewable_output_mwh": None,
        "curtailment_avoided_mwh": None,
        "verification_status": None,
        "anomaly_count": None,
        "brief_status": None,
        "data_quality_score": None,
    }

    result = record.result
    if not result:
        return summary

    summary["brief_status"] = result.get("status")

    data_quality = result.get("data_quality") or {}
    summary["data_quality_score"] = data_quality.get("completeness_score")

    forecast = result.get("forecast") or {}
    peak = forecast.get("peak") or {}
    summary["peak_demand_mw"] = peak.get("forecast_mw")

    load_balance = result.get("load_balance") or {}
    hours = load_balance.get("hours") or []
    if hours:
        summary["renewable_output_mwh"] = sum(h.get("renewable_mw", 0.0) for h in hours)

    curtailment = result.get("curtailment") or {}
    summary["curtailment_avoided_mwh"] = curtailment.get("curtailment_avoided_mwh")

    verification = result.get("verification") or {}
    if "trusted" in verification:
        summary["verification_status"] = "verified" if verification["trusted"] else "failed"

    summary["anomaly_count"] = len(result.get("anomalies") or [])

    return summary


def serialize_run_result(state: dict) -> dict[str, Any]:
    """Turn a completed (or blocked) GridState into the JSON payload for the API/SSE.

    A run whose data-quality gate hard-failed never reaches the optimizer or narrator
    (GridSentinel spec ss20: "A new run cannot proceed to optimization when required
    data fails hard quality checks") -- this returns a minimal "blocked" payload for
    that case instead of indexing keys that were never computed.
    """
    data_quality = state.get("data_quality")
    blocked = bool(data_quality and data_quality.hard_fail)

    result: dict[str, Any] = {
        "status": "blocked" if blocked else None,
        "data_quality": serialize_data_quality(data_quality),
        "progress_log": state.get("progress_log", []),
    }
    if blocked:
        return result

    verification = state["verification"]
    result.update(
        {
            "forecast": serialize_forecast(state["forecast"]),
            "forecast_backtest": serialize_backtest(state.get("forecast_backtest")),
            "anomalies": serialize_anomalies(state["anomalies"]),
            "load_balance": serialize_load_balance(state["load_balance"]),
            "curtailment": serialize_curtailment(state["curtailment"]),
            "regional_distribution": serialize_regional_distribution(state["regional_distribution"])
            if state.get("regional_distribution")
            else None,
            "regional_algorithm_comparison": serialize_algorithm_comparison(state.get("regional_algorithm_comparison")),
            "business_impact": serialize_business_impact(
                state["curtailment"],
                state.get("anomalies"),
                state.get("load_balance"),
                state.get("regional_distribution"),
                state.get("horizon_hours", 24),
            ),
            "facts": serialize_facts(state.get("facts")),
            "manifest": state.get("manifest"),
            "scenario": state.get("manifest", {}).get("scenario") if state.get("manifest") else None,
            "narrative": state["narrative"],
            "narration_provider": state["narration_provider"],
            "verification": serialize_verification(verification),
            "status": "verified" if verification.trusted else "degraded",
        }
    )
    return result
