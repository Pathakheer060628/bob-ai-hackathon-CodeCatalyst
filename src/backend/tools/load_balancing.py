"""Deterministic load-balancing optimizer via linear programming.

For each hour of a forecast horizon, decides how much to dispatch from
flexible/dispatchable generation, how much to charge/discharge a grid
battery, how much demand response (load shed) to call, and -- when supply
still cannot be absorbed or demand still cannot be met -- how much
renewable output must be curtailed or how much demand goes unmet.

This is a small linear program (~7 decision variables per hour) solved with
`scipy.optimize.linprog`. An `unmet_demand` slack variable with a very high
penalty cost is always available so the LP is never infeasible; in practice
the optimizer only uses it when dispatch + storage + demand response
genuinely cannot cover the gap, and the resulting plan surfaces that as a
reliability risk rather than silently failing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linprog

# Illustrative operating costs ($/MWh) -- configurable, not real market prices.
COST_DISPATCH_PER_MWH = 60.0
COST_SHED_PER_MWH = 200.0
COST_CURTAIL_PER_MWH = 150.0
COST_CYCLE_PER_MWH = 2.0
COST_UNMET_PER_MWH = 5000.0

N_VARS_PER_HOUR = 7  # dispatch, charge, discharge, shed, curtail, soc, unmet


@dataclass
class LoadBalanceConfig:
    dispatchable_capacity_mw: float
    storage_capacity_mwh: float = 0.0
    storage_max_rate_mw: float = 0.0
    storage_efficiency: float = 0.9
    storage_initial_soc_mwh: float = 0.0
    max_demand_response_fraction: float = 0.0


@dataclass
class HourlyAction:
    hour_index: int
    demand_mw: float
    renewable_mw: float
    dispatch_mw: float
    charge_mw: float
    discharge_mw: float
    shed_mw: float
    curtail_mw: float
    soc_mwh: float
    unmet_mw: float


@dataclass
class LoadBalancePlan:
    hours: list[HourlyAction] = field(default_factory=list)
    total_cost: float = 0.0
    total_curtailed_mwh: float = 0.0
    total_shed_mwh: float = 0.0
    total_unmet_mwh: float = 0.0
    feasible: bool = True

    @property
    def actions_needed(self) -> list[HourlyAction]:
        return [h for h in self.hours if h.shed_mw > 0.01 or h.discharge_mw > 0.01 or h.charge_mw > 0.01]


def solve_load_balance(
    demand_mw: list[float], renewable_mw: list[float], config: LoadBalanceConfig
) -> LoadBalancePlan:
    if len(demand_mw) != len(renewable_mw):
        raise ValueError("demand_mw and renewable_mw must be the same length")
    T = len(demand_mw)
    if T == 0:
        raise ValueError("Need at least one hour to plan over")

    demand = np.asarray(demand_mw, dtype=float)
    renewable = np.asarray(renewable_mw, dtype=float)

    n = N_VARS_PER_HOUR * T

    def idx(var: str, t: int) -> int:
        offset = {"dispatch": 0, "charge": 1, "discharge": 2, "shed": 3, "curtail": 4, "soc": 5, "unmet": 6}[var]
        return offset * T + t

    c = np.zeros(n)
    for t in range(T):
        c[idx("dispatch", t)] = COST_DISPATCH_PER_MWH
        c[idx("shed", t)] = COST_SHED_PER_MWH
        c[idx("curtail", t)] = COST_CURTAIL_PER_MWH
        c[idx("charge", t)] = COST_CYCLE_PER_MWH
        c[idx("discharge", t)] = COST_CYCLE_PER_MWH
        c[idx("unmet", t)] = COST_UNMET_PER_MWH

    A_eq = np.zeros((2 * T, n))
    b_eq = np.zeros(2 * T)

    for t in range(T):
        row = t
        A_eq[row, idx("dispatch", t)] = 1
        A_eq[row, idx("discharge", t)] = 1
        A_eq[row, idx("charge", t)] = -1
        A_eq[row, idx("curtail", t)] = -1
        A_eq[row, idx("shed", t)] = 1
        A_eq[row, idx("unmet", t)] = 1
        b_eq[row] = demand[t] - renewable[t]

        soc_row = T + t
        A_eq[soc_row, idx("soc", t)] = 1
        A_eq[soc_row, idx("charge", t)] = -config.storage_efficiency
        A_eq[soc_row, idx("discharge", t)] = 1.0 / config.storage_efficiency if config.storage_efficiency > 0 else 0.0
        if t == 0:
            b_eq[soc_row] = config.storage_initial_soc_mwh
        else:
            A_eq[soc_row, idx("soc", t - 1)] = -1

    bounds = []
    for t in range(T):
        bounds.append((0, config.dispatchable_capacity_mw))  # dispatch
    for t in range(T):
        bounds.append((0, config.storage_max_rate_mw))  # charge
    for t in range(T):
        bounds.append((0, config.storage_max_rate_mw))  # discharge
    for t in range(T):
        bounds.append((0, max(0.0, config.max_demand_response_fraction * demand[t])))  # shed
    for t in range(T):
        bounds.append((0, max(0.0, renewable[t])))  # curtail
    for t in range(T):
        bounds.append((0, config.storage_capacity_mwh))  # soc
    for t in range(T):
        bounds.append((0, None))  # unmet

    result = linprog(c=c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

    if not result.success:
        return LoadBalancePlan(hours=[], total_cost=0.0, feasible=False)

    x = result.x
    hours = []
    for t in range(T):
        hours.append(
            HourlyAction(
                hour_index=t,
                demand_mw=round(float(demand[t]), 1),
                renewable_mw=round(float(renewable[t]), 1),
                dispatch_mw=round(float(x[idx("dispatch", t)]), 1),
                charge_mw=round(float(x[idx("charge", t)]), 1),
                discharge_mw=round(float(x[idx("discharge", t)]), 1),
                shed_mw=round(float(x[idx("shed", t)]), 1),
                curtail_mw=round(float(x[idx("curtail", t)]), 1),
                soc_mwh=round(float(x[idx("soc", t)]), 1),
                unmet_mw=round(float(x[idx("unmet", t)]), 1),
            )
        )

    return LoadBalancePlan(
        hours=hours,
        total_cost=round(float(result.fun), 2),
        total_curtailed_mwh=round(sum(h.curtail_mw for h in hours), 1),
        total_shed_mwh=round(sum(h.shed_mw for h in hours), 1),
        total_unmet_mwh=round(sum(h.unmet_mw for h in hours), 1),
        feasible=True,
    )
