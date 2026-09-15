"""LangGraph pipeline wiring the deterministic grid-optimisation tools together.

forecast_demand_node -> detect_anomalies_node -> root_cause_node ->
load_balance_node -> curtailment_node -> narrate_node -> verify_node

Every node does exactly one job and writes typed results into `GridState`;
nothing in this file computes a number itself beyond simple aggregation
(building the lists the tools need) -- all the real math lives in
`backend/tools/*`. `stream_pipeline` yields the state after each node so the
API layer can turn that into an SSE progress feed.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Annotated, Any, TypedDict

import pandas as pd
from langgraph.graph import END, StateGraph

from backend.llm.provider import get_provider
from backend.tools.anomaly_detection import ASSET_COLUMNS, detect_renewable_anomalies
from backend.tools.curtailment import CurtailmentPlan, minimize_curtailment
from backend.tools.forecasting import ForecastResult, forecast_demand, forecast_renewable_supply
from backend.tools.load_balancing import LoadBalanceConfig, LoadBalancePlan, solve_load_balance
from backend.tools.root_cause import RootCauseFinding, classify_root_cause
from backend.agents.verifier import VerificationResult, verify_brief

MAX_ANOMALY_FINDINGS = 8


class GridState(TypedDict, total=False):
    history: pd.DataFrame
    full_history: pd.DataFrame
    horizon_hours: int
    load_balance_config: LoadBalanceConfig

    forecast: ForecastResult
    renewable_forecast_mw: list[float]
    anomalies: list[RootCauseFinding]
    load_balance: LoadBalancePlan
    curtailment: CurtailmentPlan
    narrative: str
    narration_provider: str
    verification: VerificationResult
    progress_log: Annotated[list[str], operator.add]


def default_load_balance_config(history: pd.DataFrame) -> LoadBalanceConfig:
    peak_load = float(history["load_actual_mw"].max())
    return LoadBalanceConfig(
        dispatchable_capacity_mw=round(peak_load * 0.9, -2),
        storage_capacity_mwh=round(peak_load * 0.08, -2),
        storage_max_rate_mw=round(peak_load * 0.04, -2),
        storage_efficiency=0.9,
        storage_initial_soc_mwh=round(peak_load * 0.04, -2),
        max_demand_response_fraction=0.05,
    )


def node_forecast(state: GridState) -> dict:
    horizon = state.get("horizon_hours", 24)
    history = state["history"]
    full_history = state["full_history"]

    forecast = forecast_demand(history["load_actual_mw"], horizon_hours=horizon)
    renewable_forecast = forecast_renewable_supply(
        full_history, start=history.index.max() + pd.Timedelta(hours=1), horizon_hours=horizon
    )
    return {
        "forecast": forecast,
        "renewable_forecast_mw": renewable_forecast,
        "progress_log": [
            f"Forecast complete: peak {forecast.peak.forecast_mw:,.0f} MW, "
            f"{len(forecast.spikes)} spike hour(s) flagged."
        ],
    }


def node_detect_anomalies_and_root_cause(state: GridState) -> dict:
    history = state["history"]
    full_history = state["full_history"]

    findings: list[RootCauseFinding] = []
    log_lines = []
    for asset in ASSET_COLUMNS:
        result = detect_renewable_anomalies(history, full_history, asset)
        log_lines.append(f"{asset}: {len(result.episodes)} anomaly episode(s) detected.")
        for episode in result.episodes:
            findings.append(classify_root_cause(episode, history, full_history))

    findings.sort(key=lambda f: f.episode.duration_hours, reverse=True)
    findings = findings[:MAX_ANOMALY_FINDINGS]

    return {"anomalies": findings, "progress_log": log_lines}


def node_load_balance(state: GridState) -> dict:
    demand = [h.forecast_mw for h in state["forecast"].hourly]
    renewable = state["renewable_forecast_mw"]
    config = state.get("load_balance_config") or default_load_balance_config(state["history"])

    plan = solve_load_balance(demand, renewable, config)
    msg = (
        f"Load-balance plan solved: est. cost ${plan.total_cost:,.0f}, "
        f"{plan.total_curtailed_mwh:,.0f} MWh curtailed, {plan.total_unmet_mwh:,.0f} MWh unmet."
        if plan.feasible
        else "Load-balance LP infeasible."
    )
    return {"load_balance": plan, "load_balance_config": config, "progress_log": [msg]}


def node_curtailment(state: GridState) -> dict:
    demand = [h.forecast_mw for h in state["forecast"].hourly]
    renewable = state["renewable_forecast_mw"]
    config = state["load_balance_config"]

    plan = minimize_curtailment(demand, renewable, config)
    msg = (
        f"Curtailment plan: {plan.curtailment_avoided_mwh:,.0f} MWh avoided "
        f"({plan.curtailment_reduction_pct:.1f}% reduction vs. baseline)."
    )
    return {"curtailment": plan, "progress_log": [msg]}


def _narration_context(state: GridState) -> dict:
    return {
        "forecast": state.get("forecast"),
        "anomalies": state.get("anomalies", []),
        "load_balance": state.get("load_balance"),
        "curtailment": state.get("curtailment"),
    }


def node_narrate(state: GridState) -> dict:
    provider = get_provider()
    narrative = provider.narrate(_narration_context(state))
    return {
        "narrative": narrative,
        "narration_provider": provider.name,
        "progress_log": [f"Brief narrated by '{provider.name}' provider."],
    }


def node_verify(state: GridState) -> dict:
    result = verify_brief(state["narrative"], _narration_context(state))
    msg = (
        "Verifier: all narrated numbers trace back to computed state."
        if result.trusted
        else f"Verifier FLAGGED {len(result.unverified_numbers)} unverified number(s) in the brief."
    )
    return {"verification": result, "progress_log": [msg]}


def build_graph():
    graph = StateGraph(GridState)
    graph.add_node("forecast", node_forecast)
    graph.add_node("anomalies", node_detect_anomalies_and_root_cause)
    graph.add_node("load_balance", node_load_balance)
    graph.add_node("curtailment", node_curtailment)
    graph.add_node("narrate", node_narrate)
    graph.add_node("verify", node_verify)

    graph.set_entry_point("forecast")
    graph.add_edge("forecast", "anomalies")
    graph.add_edge("anomalies", "load_balance")
    graph.add_edge("load_balance", "curtailment")
    graph.add_edge("curtailment", "narrate")
    graph.add_edge("narrate", "verify")
    graph.add_edge("verify", END)
    return graph.compile()


@dataclass
class PipelineRequest:
    history: pd.DataFrame
    full_history: pd.DataFrame
    horizon_hours: int = 24
    load_balance_config: LoadBalanceConfig | None = None


def run_pipeline(request: PipelineRequest) -> GridState:
    app = build_graph()
    initial: GridState = {
        "history": request.history,
        "full_history": request.full_history,
        "horizon_hours": request.horizon_hours,
        "progress_log": [],
    }
    if request.load_balance_config:
        initial["load_balance_config"] = request.load_balance_config
    result: GridState = app.invoke(initial)
    return result


def stream_pipeline(request: PipelineRequest):
    """Yields (node_name, partial_state_update) for each completed node -- for SSE progress."""
    app = build_graph()
    initial: GridState = {
        "history": request.history,
        "full_history": request.full_history,
        "horizon_hours": request.horizon_hours,
        "progress_log": [],
    }
    if request.load_balance_config:
        initial["load_balance_config"] = request.load_balance_config

    for event in app.stream(initial):
        for node_name, update in event.items():
            yield node_name, update
