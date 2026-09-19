"""LangGraph pipeline wiring the deterministic grid-optimisation tools together.

data_quality_node -> [blocked | forecast_node -> anomalies_node ->
load_balance_node -> curtailment_node -> regional_distribution_node ->
facts_node -> narrate_node -> verify_node]

The data-quality gate runs first and can short-circuit the run to `blocked` before
any forecast/optimizer/narrator code sees the data (GridSentinel spec ss20: a run
must not proceed to optimization on data that fails a hard quality check).

Every node does exactly one job and writes typed results into `GridState`;
nothing in this file computes a number itself beyond simple aggregation
(building the lists the tools need) -- all the real math lives in
`backend/tools/*`. `stream_pipeline` yields the state after each node so the
API layer can turn that into an SSE progress feed.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import operator
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, TypedDict

import pandas as pd
from langgraph.graph import END, StateGraph

from backend.llm.provider import get_provider
from backend.ml.ml_forecasting import ModelNotTrainedError, is_model_available, ml_forecast_demand
from backend.tools.anomaly_detection import ASSET_COLUMNS, detect_renewable_anomalies
from backend.tools.curtailment import CurtailmentPlan, minimize_curtailment
from backend.tools.data_quality import DataQualityReport, assess_window_quality
from backend.tools.facts import Fact, build_fact_ledger
from backend.tools.forecasting import (
    BacktestResult,
    ForecastResult,
    backtest_demand_forecast,
    forecast_demand,
    forecast_renewable_supply,
)
from backend.tools.load_balancing import LoadBalanceConfig, LoadBalancePlan, solve_load_balance
from backend.tools.regional_distribution import RegionalDistributionPlan, solve_regional_distribution
from backend.tools.root_cause import RootCauseFinding, classify_root_cause
from backend.agents.verifier import VerificationResult, verify_brief

MODEL_VERSIONS = {
    "forecast": "seasonal-naive-trend-v1",
    "anomaly_detection": "cusum-seasonal-v1",
    "root_cause": "rule-based-elimination-v2",
    "optimizer": "scipy-linprog-highs",
}


@dataclass
class ScenarioConfig:
    """A reproducible what-if scenario applied to the forecast outputs (GridSentinel spec ss7).

    Scales the *forecast*, not the raw history, so observed and simulated figures stay
    clearly separated -- the pipeline never mutates the historical record, and every
    scaled run is unmistakably logged as simulated in the progress log and manifest.
    """

    scenario_id: str | None = None
    renewable_scale: float = 1.0
    demand_scale: float = 1.0
    label: str | None = None

    @property
    def is_active(self) -> bool:
        return self.renewable_scale != 1.0 or self.demand_scale != 1.0


class GridState(TypedDict, total=False):
    run_id: str
    history: pd.DataFrame
    full_history: pd.DataFrame
    horizon_hours: int
    load_balance_config: LoadBalanceConfig
    scenario: ScenarioConfig
    forecast_model: str  # "seasonal" (default, deterministic) or "ml" (trained HistGradientBoostingRegressor)

    data_quality: DataQualityReport
    forecast: ForecastResult
    forecast_backtest: BacktestResult
    renewable_forecast_mw: list[float]
    anomalies: list[RootCauseFinding]
    load_balance: LoadBalancePlan
    curtailment: CurtailmentPlan
    regional_distribution: RegionalDistributionPlan
    facts: list[Fact]
    manifest: dict[str, Any]
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


def node_data_quality(state: GridState) -> dict:
    report = assess_window_quality(state["history"])
    if report.hard_fail:
        msg = "Data-quality gate BLOCKED this run: " + "; ".join(report.hard_fail_reasons)
    elif report.warnings:
        msg = f"Data-quality gate passed with warnings ({report.completeness_score:.0%} complete): " + "; ".join(
            report.warnings
        )
    else:
        msg = f"Data-quality gate passed: {report.completeness_score:.0%} complete, no issues found."
    return {"data_quality": report, "progress_log": [msg]}


def route_after_data_quality(state: GridState) -> str:
    return "blocked" if state["data_quality"].hard_fail else "proceed"


def node_blocked(state: GridState) -> dict:
    reasons = "; ".join(state["data_quality"].hard_fail_reasons)
    return {"progress_log": [f"Run halted before optimization: {reasons}"]}


def _apply_scenario(forecast: ForecastResult, renewable_forecast_mw: list[float], scenario: ScenarioConfig):
    d_scale, r_scale = scenario.demand_scale, scenario.renewable_scale
    for h in forecast.hourly:
        h.forecast_mw = round(h.forecast_mw * d_scale, 1)
        h.baseline_mw = round(h.baseline_mw * d_scale, 1)
        h.baseline_std_mw = round(h.baseline_std_mw * d_scale, 1)
        h.upper_bound_mw = round(h.forecast_mw + 1.96 * h.baseline_std_mw, 1)
        h.lower_bound_mw = round(max(0.0, h.forecast_mw - 1.96 * h.baseline_std_mw), 1)
        h.spike_severity_std = round(
            (h.forecast_mw - h.baseline_mw) / h.baseline_std_mw, 2
        ) if h.baseline_std_mw > 0 else 0.0
        h.is_spike = bool(h.spike_severity_std > forecast.spike_std_threshold)

    scaled_renewable = [round(v * r_scale, 1) for v in renewable_forecast_mw]
    return forecast, scaled_renewable


def node_forecast(state: GridState) -> dict:
    horizon = state.get("horizon_hours", 24)
    history = state["history"]
    full_history = state["full_history"]
    scenario = state.get("scenario")
    forecast_model = state.get("forecast_model", "seasonal")

    log_lines: list[str] = []
    if forecast_model == "ml" and is_model_available():
        try:
            forecast = ml_forecast_demand(history, full_history, horizon_hours=horizon)
            log_lines.append("Demand forecast produced by trained ML model (HistGradientBoostingRegressor).")
        except ModelNotTrainedError:
            forecast = forecast_demand(history["load_actual_mw"], horizon_hours=horizon)
            log_lines.append("ML model unavailable -- fell back to seasonal-naive forecast.")
    else:
        if forecast_model == "ml":
            log_lines.append("ML model not trained yet -- using seasonal-naive forecast.")
        forecast = forecast_demand(history["load_actual_mw"], horizon_hours=horizon)

    renewable_forecast = forecast_renewable_supply(
        full_history, start=history.index.max() + pd.Timedelta(hours=1), horizon_hours=horizon
    )
    backtest = backtest_demand_forecast(history["load_actual_mw"], horizon_hours=horizon)

    log_lines.append(
        f"Forecast complete: peak {forecast.peak.forecast_mw:,.0f} MW, "
        f"{len(forecast.spikes)} spike hour(s) flagged."
    )
    if backtest.n_points:
        log_lines.append(
            f"Backtest: MAE {backtest.mae:,.0f} MW vs. naive-baseline MAE {backtest.naive_mae:,.0f} MW "
            f"({backtest.improvement_pct:+.1f}% improvement over {backtest.n_folds} fold(s))."
        )

    if scenario and scenario.is_active:
        forecast, renewable_forecast = _apply_scenario(forecast, renewable_forecast, scenario)
        log_lines.append(
            f"SIMULATED SCENARIO applied (scenario_id={scenario.scenario_id}): "
            f"demand x{scenario.demand_scale}, renewable x{scenario.renewable_scale} -- "
            "figures from this point on are simulated, not observed history."
        )

    return {
        "forecast": forecast,
        "renewable_forecast_mw": renewable_forecast,
        "forecast_backtest": backtest,
        "progress_log": log_lines,
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

    # Rank by estimated $ cost exposure first, not just how long an episode lasted or
    # how confident the root-cause call is -- a low-confidence, short-lived anomaly on
    # a large asset can carry more real cost than a long, high-confidence one on a
    # small asset, and that's what an operator should see first. Every detected episode
    # is returned (with its own recommended action) -- none are dropped.
    findings.sort(key=lambda f: (f.estimated_cost_usd, f.episode.duration_hours), reverse=True)

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


def node_regional_distribution(state: GridState) -> dict:
    # The forecast's peak hour is the representative "worst case" snapshot for
    # regional routing -- if every region's need is coverable at peak demand,
    # it's coverable at every lighter hour too.
    peak_demand_mw = state["forecast"].peak.forecast_mw
    plan = solve_regional_distribution(peak_demand_mw)

    if plan.total_unmet_mw > 0.5:
        msg = (
            f"Regional distribution: {plan.overall_fulfillment_pct:.1f}% of peak demand covered "
            f"at least-cost routing -- {plan.total_unmet_mw:,.0f} MW shortfall identified, fallback "
            "recommendations attached per region."
        )
    else:
        msg = (
            f"Regional distribution: 100% of peak demand ({plan.total_demand_mw:,.0f} MW) covered "
            f"across {len(plan.regions)} regions at least-cost routing "
            f"(${plan.total_transmission_cost_usd:,.0f} transmission cost)."
        )
    return {"regional_distribution": plan, "progress_log": [msg]}


@lru_cache(maxsize=1)
def _git_sha() -> str:
    try:
        repo_root = Path(__file__).resolve().parents[3]
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def _config_hash(config: LoadBalanceConfig | None) -> str:
    if config is None:
        return "default"
    payload = json.dumps(dataclasses.asdict(config), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def node_facts(state: GridState) -> dict:
    history = state["history"]
    full_history = state["full_history"]
    scenario = state.get("scenario")

    facts = build_fact_ledger(state, run_id=state.get("run_id") or "run")
    manifest = {
        "data_window": {
            "start": history.index.min().isoformat(),
            "end": history.index.max().isoformat(),
            "rows": int(len(history)),
        },
        "full_dataset_window": {
            "start": full_history.index.min().isoformat(),
            "end": full_history.index.max().isoformat(),
        },
        "model_versions": MODEL_VERSIONS,
        "code_version": _git_sha(),
        "verifier_version": "regex-numeric-tolerance-v1",
        "config_hash": _config_hash(state.get("load_balance_config")),
        "scenario": dataclasses.asdict(scenario) if scenario else None,
    }
    return {
        "facts": facts,
        "manifest": manifest,
        "progress_log": [f"Fact ledger built: {len(facts)} provenance-tagged fact(s)."],
    }


def _narration_context(state: GridState) -> dict:
    return {
        "forecast": state.get("forecast"),
        "anomalies": state.get("anomalies", []),
        "load_balance": state.get("load_balance"),
        "curtailment": state.get("curtailment"),
        "regional_distribution": state.get("regional_distribution"),
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
    graph.add_node("data_quality", node_data_quality)
    graph.add_node("blocked", node_blocked)
    graph.add_node("forecast", node_forecast)
    graph.add_node("anomalies", node_detect_anomalies_and_root_cause)
    graph.add_node("load_balance", node_load_balance)
    graph.add_node("curtailment", node_curtailment)
    graph.add_node("regional_distribution", node_regional_distribution)
    graph.add_node("facts", node_facts)
    graph.add_node("narrate", node_narrate)
    graph.add_node("verify", node_verify)

    graph.set_entry_point("data_quality")
    graph.add_conditional_edges(
        "data_quality", route_after_data_quality, {"proceed": "forecast", "blocked": "blocked"}
    )
    graph.add_edge("blocked", END)
    graph.add_edge("forecast", "anomalies")
    graph.add_edge("anomalies", "load_balance")
    graph.add_edge("load_balance", "curtailment")
    graph.add_edge("curtailment", "regional_distribution")
    graph.add_edge("regional_distribution", "facts")
    graph.add_edge("facts", "narrate")
    graph.add_edge("narrate", "verify")
    graph.add_edge("verify", END)
    return graph.compile()


@dataclass
class PipelineRequest:
    history: pd.DataFrame
    full_history: pd.DataFrame
    horizon_hours: int = 24
    load_balance_config: LoadBalanceConfig | None = None
    scenario: ScenarioConfig | None = None
    run_id: str | None = None
    forecast_model: str = "seasonal"


def _initial_state(request: PipelineRequest) -> GridState:
    initial: GridState = {
        "history": request.history,
        "full_history": request.full_history,
        "horizon_hours": request.horizon_hours,
        "forecast_model": request.forecast_model,
        "progress_log": [],
    }
    if request.run_id:
        initial["run_id"] = request.run_id
    if request.load_balance_config:
        initial["load_balance_config"] = request.load_balance_config
    if request.scenario:
        initial["scenario"] = request.scenario
    return initial


def run_pipeline(request: PipelineRequest) -> GridState:
    app = build_graph()
    result: GridState = app.invoke(_initial_state(request))
    return result


def stream_pipeline(request: PipelineRequest):
    """Yields (node_name, partial_state_update) for each completed node -- for SSE progress."""
    app = build_graph()
    for event in app.stream(_initial_state(request)):
        for node_name, update in event.items():
            yield node_name, update
