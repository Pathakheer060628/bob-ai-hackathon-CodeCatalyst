"""Pluggable narration provider.

The rule enforced throughout this backend: every number in a brief comes
from a deterministic tool (forecasting, anomaly detection, root-cause,
load-balancing, curtailment) -- an LLM provider only phrases those already-
computed numbers into prose. It never calculates anything itself. The
verifier agent (`backend/agents/verifier.py`) enforces this by re-extracting
every number from the generated text and checking it traces back to the
computed state.

`TemplateNarrationProvider` is the default: fully offline, deterministic
string templating, zero network/API-key dependency. `get_provider()` swaps
in `BobWatsonxProvider` (backend/llm/bob_provider.py) when
`NARRATION_PROVIDER=bob` is set and an API key is configured.
"""

from __future__ import annotations

import os
from typing import Protocol


class NarrationProvider(Protocol):
    def narrate(self, context: dict) -> str: ...


class TemplateNarrationProvider:
    """Deterministic, offline narration -- string templates over computed state."""

    name = "template-offline"

    def narrate(self, context: dict) -> str:
        parts = [
            narrate_forecast(context.get("forecast")),
            narrate_anomalies(context.get("anomalies", [])),
            narrate_load_balance(context.get("load_balance")),
            narrate_curtailment(context.get("curtailment")),
        ]
        return "\n\n".join(p for p in parts if p)


def narrate_forecast(forecast) -> str:
    if not forecast:
        return ""
    peak = forecast.peak
    lines = [
        f"**Demand Forecast** ({len(forecast.hourly)}h horizon, trend factor {forecast.trend_factor}x "
        f"vs. {forecast.lookback_weeks}-week seasonal baseline):"
    ]
    if peak:
        lines.append(
            f"- Peak forecast demand: {peak.forecast_mw:,.0f} MW at "
            f"{peak.timestamp.strftime('%Y-%m-%d %H:%M UTC')} "
            f"(expected range {peak.lower_bound_mw:,.0f}-{peak.upper_bound_mw:,.0f} MW)."
        )
    spikes = forecast.spikes
    if spikes:
        lines.append(
            f"- {len(spikes)} hour(s) flagged as demand spikes (>{forecast.spike_std_threshold} "
            f"std above seasonal baseline), the most severe at "
            f"{spikes[0].timestamp.strftime('%Y-%m-%d %H:%M UTC')} "
            f"({spikes[0].spike_severity_std} std above baseline)."
        )
    else:
        lines.append("- No demand spikes flagged in this horizon.")
    return "\n".join(lines)


def narrate_anomalies(anomaly_findings) -> str:
    if not anomaly_findings:
        return "**Renewable Performance:** No sustained anomalies detected in any asset class."
    lines = ["**Renewable Performance Anomalies:**"]
    for finding in anomaly_findings:
        ep = finding.episode
        lines.append(
            f"- {ep.asset}: {ep.direction}performance from {ep.start.strftime('%Y-%m-%d %H:%M')} "
            f"to {ep.end.strftime('%Y-%m-%d %H:%M')} UTC ({ep.duration_hours}h, avg deviation "
            f"{ep.avg_deviation:+.1%} capacity factor). Root cause: {finding.label}."
        )
    return "\n".join(lines)


def narrate_load_balance(plan) -> str:
    if not plan or not plan.feasible:
        return ""
    lines = [
        "**Load-Balancing Recommendation:**",
        f"- Estimated operating cost for this horizon: ${plan.total_cost:,.0f}.",
    ]
    if plan.total_unmet_mwh > 0:
        lines.append(
            f"- WARNING: {plan.total_unmet_mwh:,.1f} MWh of demand is projected unmet -- "
            "dispatchable capacity and flexibility are insufficient for this horizon."
        )
    if plan.total_shed_mwh > 0:
        lines.append(f"- {plan.total_shed_mwh:,.1f} MWh of demand response (load shed) recommended.")
    n_actions = len(plan.actions_needed)
    if n_actions:
        lines.append(f"- {n_actions} hour(s) call for active storage or demand-response action.")
    return "\n".join(lines)


def narrate_curtailment(plan) -> str:
    if not plan:
        return ""
    lines = [
        "**Curtailment Minimization Plan:**",
        f"- Baseline (no storage/demand-response) curtailment: {plan.baseline_curtailed_mwh:,.1f} MWh.",
        f"- Optimized plan curtailment: {plan.optimized_curtailed_mwh:,.1f} MWh.",
        f"- Curtailment avoided: {plan.curtailment_avoided_mwh:,.1f} MWh "
        f"({plan.curtailment_reduction_pct:.1f}% reduction).",
    ]
    return "\n".join(lines)


def get_provider() -> NarrationProvider:
    provider_name = os.environ.get("NARRATION_PROVIDER", "template").lower()
    if provider_name == "bob":
        from backend.llm.bob_provider import BobWatsonxProvider

        return BobWatsonxProvider()
    return TemplateNarrationProvider()
