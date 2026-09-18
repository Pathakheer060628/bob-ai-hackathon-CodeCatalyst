"""Curtailment minimization plan.

Runs the load-balancing LP (`tools.load_balancing.solve_load_balance`) twice
over the same demand/renewable forecast:

- **baseline**: no storage, no demand response -- only dispatchable
  generation can respond, so any renewable oversupply beyond what dispatch
  can back down for is curtailed. This represents today's typical
  operating posture.
- **optimized**: the full configured flexibility (battery storage + demand
  response), which absorbs oversupply into storage or shifts it into load
  instead of curtailing it.

The difference between the two curtailed totals is the plan's headline
number: how much clean energy the recommended actions actually save.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from backend.tools.load_balancing import (
    HourlyAction,
    LoadBalanceConfig,
    LoadBalancePlan,
    solve_load_balance,
)


@dataclass
class CurtailmentPlan:
    baseline: LoadBalancePlan
    optimized: LoadBalancePlan
    baseline_curtailed_mwh: float
    optimized_curtailed_mwh: float
    curtailment_avoided_mwh: float
    curtailment_reduction_pct: float
    recommended_actions: list[HourlyAction]


def minimize_curtailment(
    demand_mw: list[float], renewable_mw: list[float], config: LoadBalanceConfig
) -> CurtailmentPlan:
    # storage_initial_soc_mwh must be zeroed along with capacity/rate: the SOC
    # balance equation in solve_load_balance() requires soc[0] == storage_initial_soc_mwh,
    # but with storage_capacity_mwh=0 the soc variable is bounded to [0, 0] -- leaving a
    # nonzero initial SOC here makes the equation unsatisfiable and the baseline LP
    # infeasible on every run, which silently zeroed out curtailment_avoided_mwh (or,
    # once the optimized plan curtails anything, makes it go negative).
    baseline_config = replace(
        config,
        storage_capacity_mwh=0.0,
        storage_max_rate_mw=0.0,
        storage_initial_soc_mwh=0.0,
        max_demand_response_fraction=0.0,
    )
    baseline = solve_load_balance(demand_mw, renewable_mw, baseline_config)
    optimized = solve_load_balance(demand_mw, renewable_mw, config)

    baseline_curtailed = baseline.total_curtailed_mwh if baseline.feasible else 0.0
    optimized_curtailed = optimized.total_curtailed_mwh if optimized.feasible else 0.0
    avoided = round(baseline_curtailed - optimized_curtailed, 1)
    reduction_pct = round((avoided / baseline_curtailed) * 100, 1) if baseline_curtailed > 0 else 0.0

    recommended = optimized.actions_needed if optimized.feasible else []

    return CurtailmentPlan(
        baseline=baseline,
        optimized=optimized,
        baseline_curtailed_mwh=baseline_curtailed,
        optimized_curtailed_mwh=optimized_curtailed,
        curtailment_avoided_mwh=avoided,
        curtailment_reduction_pct=reduction_pct,
        recommended_actions=recommended,
    )
