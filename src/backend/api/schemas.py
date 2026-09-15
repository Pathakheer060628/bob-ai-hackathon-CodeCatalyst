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


class RunCreateRequest(BaseModel):
    window_end: str = Field(..., description="ISO timestamp: the 'as-of-now' point for the run")
    lookback_days: int = Field(30, ge=7, le=365)
    horizon_hours: int = Field(24, ge=1, le=72)
    load_balance_config: LoadBalanceConfigIn | None = None


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
            }
        )
    return out


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
    return {
        "baseline_curtailed_mwh": plan.baseline_curtailed_mwh,
        "optimized_curtailed_mwh": plan.optimized_curtailed_mwh,
        "curtailment_avoided_mwh": plan.curtailment_avoided_mwh,
        "curtailment_reduction_pct": plan.curtailment_reduction_pct,
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


def serialize_verification(result) -> dict[str, Any]:
    return {
        "trusted": result.trusted,
        "checked_count": len(result.checked_numbers),
        "unverified_numbers": result.unverified_numbers,
        "trusted_pool_size": result.trusted_pool_size,
    }


def serialize_run_result(state: dict) -> dict[str, Any]:
    return {
        "forecast": serialize_forecast(state["forecast"]),
        "anomalies": serialize_anomalies(state["anomalies"]),
        "load_balance": serialize_load_balance(state["load_balance"]),
        "curtailment": serialize_curtailment(state["curtailment"]),
        "narrative": state["narrative"],
        "narration_provider": state["narration_provider"],
        "verification": serialize_verification(state["verification"]),
        "progress_log": state["progress_log"],
    }
