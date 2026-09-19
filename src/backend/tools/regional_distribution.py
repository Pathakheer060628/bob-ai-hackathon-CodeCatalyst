"""Regional power distribution: population-weighted demand per region, routed
from the nearest generation station, cost-optimized via linear programming.

Answers three questions the national-aggregate pipeline can't on its own:
  1. How much power does each region actually need? (population-weighted
     share of the pipeline's own forecasted national demand -- not a new
     demand model, just splitting an already-computed number.)
  2. Which generation station is closest to each region, and how far away
     is it? (great-circle / haversine distance over the reference
     coordinates in backend/data/regions.py.)
  3. Given limited station capacity, how should available power be routed
     to minimize transmission cost while meeting each region's need --
     and if total capacity can't cover total demand, which regions come up
     short, by how much, and what's the recommended mitigation?

The routing problem is a classic transportation LP, solved the same way
backend/tools/load_balancing.py solves dispatch: minimize routing cost with
an always-available "unmet demand" slack variable at a very high penalty, so
the solver is never infeasible -- a real shortfall shows up as a priced,
per-region unmet amount instead of the whole run failing. Because shorter
routes are cheaper, the optimizer naturally prioritizes serving each region
from its nearest station first and only reaches for farther/costlier routes
once nearby capacity is exhausted -- exactly the "nearest station serves its
area's need first" behavior this module was asked for.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linprog

from backend.data.regions import REGIONS, STATIONS, TOTAL_POPULATION, Region, Station

# Illustrative transmission cost rate ($ per MW moved per km) -- same spirit
# as the illustrative $/MWh rates in load_balancing.py: not a real tariff,
# but a stand-in that makes "prefer the nearer station" a genuine cost
# incentive for the LP rather than an assumption baked into the code.
COST_PER_MW_KM = 0.08
PENALTY_UNMET_PER_MW = 100_000.0  # keeps the LP always feasible; a real shortfall is still very expensive


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


@dataclass
class RegionAllocation:
    region: str
    population: int
    demand_mw: float
    nearest_station: str
    nearest_station_distance_km: float
    allocated_mw: float
    unmet_mw: float
    fulfillment_pct: float
    transmission_cost_usd: float
    recommended_action: str = ""


@dataclass
class RegionalDistributionPlan:
    regions: list[RegionAllocation] = field(default_factory=list)
    total_demand_mw: float = 0.0
    total_allocated_mw: float = 0.0
    total_unmet_mw: float = 0.0
    total_transmission_cost_usd: float = 0.0
    overall_fulfillment_pct: float = 100.0
    total_station_capacity_mw: float = 0.0
    feasible: bool = True
    system_recommendation: str = ""


def _region_recommendation(region: Region, station: Station, unmet_mw: float) -> str:
    if unmet_mw <= 0.5:
        return f"Need fully met from {station.name} ({haversine_km(region.lat, region.lon, station.lat, station.lon):.0f} km)."
    return (
        f"Shortfall of {unmet_mw:,.0f} MW -- nearest station ({station.name}) is at capacity. "
        f"Recommend demand-response/load-shedding for this shortfall, or new dispatchable/storage capacity "
        f"sited closer to {region.name} to reduce reliance on longer, costlier routes."
    )


def solve_regional_distribution(national_demand_mw: float) -> RegionalDistributionPlan:
    """Allocate `national_demand_mw` (the pipeline's own forecasted demand for
    one representative hour, typically its peak) across regions, proportional
    to each region's population share, routed from the least-cost combination
    of stations.
    """
    if national_demand_mw <= 0:
        raise ValueError("national_demand_mw must be positive")

    n_stations, n_regions = len(STATIONS), len(REGIONS)
    demand = [national_demand_mw * (r.population / TOTAL_POPULATION) for r in REGIONS]

    distances = [
        [haversine_km(s.lat, s.lon, r.lat, r.lon) for r in REGIONS] for s in STATIONS
    ]
    cost = [[d * COST_PER_MW_KM for d in row] for row in distances]

    # variables: x[i,j] (station i -> region j) flattened, then unmet[j]
    n_x = n_stations * n_regions

    def x_idx(i: int, j: int) -> int:
        return i * n_regions + j

    def unmet_idx(j: int) -> int:
        return n_x + j

    n_vars = n_x + n_regions
    c = np.zeros(n_vars)
    for i in range(n_stations):
        for j in range(n_regions):
            c[x_idx(i, j)] = cost[i][j]
    for j in range(n_regions):
        c[unmet_idx(j)] = PENALTY_UNMET_PER_MW

    # demand equality: sum_i x[i,j] + unmet[j] = demand[j]
    A_eq = np.zeros((n_regions, n_vars))
    b_eq = np.zeros(n_regions)
    for j in range(n_regions):
        for i in range(n_stations):
            A_eq[j, x_idx(i, j)] = 1
        A_eq[j, unmet_idx(j)] = 1
        b_eq[j] = demand[j]

    # capacity inequality: sum_j x[i,j] <= capacity[i]
    A_ub = np.zeros((n_stations, n_vars))
    b_ub = np.zeros(n_stations)
    for i, station in enumerate(STATIONS):
        for j in range(n_regions):
            A_ub[i, x_idx(i, j)] = 1
        b_ub[i] = station.capacity_mw

    bounds = [(0, None)] * n_vars

    result = linprog(c=c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

    total_capacity = sum(s.capacity_mw for s in STATIONS)
    if not result.success:
        # Should not happen given the unmet slack, but stay honest if the solver
        # itself fails rather than silently returning a fabricated plan.
        return RegionalDistributionPlan(
            regions=[],
            total_demand_mw=round(national_demand_mw, 1),
            total_station_capacity_mw=total_capacity,
            feasible=False,
            system_recommendation="Solver failed to find any allocation -- check station/region reference data.",
        )

    x = result.x
    allocations: list[RegionAllocation] = []
    total_allocated = 0.0
    total_unmet = 0.0
    total_cost = 0.0

    for j, region in enumerate(REGIONS):
        allocated = sum(x[x_idx(i, j)] for i in range(n_stations))
        unmet = x[unmet_idx(j)]
        region_cost = sum(x[x_idx(i, j)] * cost[i][j] for i in range(n_stations))

        nearest_i = min(range(n_stations), key=lambda i: distances[i][j])
        nearest_station = STATIONS[nearest_i]

        total_allocated += allocated
        total_unmet += unmet
        total_cost += region_cost

        allocations.append(
            RegionAllocation(
                region=region.name,
                population=region.population,
                demand_mw=round(demand[j], 1),
                nearest_station=nearest_station.name,
                nearest_station_distance_km=round(distances[nearest_i][j], 1),
                allocated_mw=round(allocated, 1),
                unmet_mw=round(unmet, 1),
                fulfillment_pct=round((allocated / demand[j]) * 100, 1) if demand[j] > 0 else 100.0,
                transmission_cost_usd=round(region_cost, 2),
                recommended_action=_region_recommendation(region, nearest_station, unmet),
            )
        )

    # Costliest shortfalls first, so the system-level recommendation reads
    # like a prioritized action list, not just a list order.
    allocations.sort(key=lambda a: a.unmet_mw, reverse=True)

    if total_unmet > 0.5:
        worst = [a for a in allocations if a.unmet_mw > 0.5][:3]
        system_recommendation = (
            f"National shortfall of {total_unmet:,.0f} MW ({total_unmet / national_demand_mw * 100:.1f}% of demand) "
            f"-- total station capacity ({total_capacity:,.0f} MW) cannot fully cover this hour's requirement. "
            "Priority regions for demand-response or new capacity: "
            + ", ".join(f"{a.region} ({a.unmet_mw:,.0f} MW short)" for a in worst)
            + "."
        )
    else:
        system_recommendation = "All regional demand met within station capacity at least-cost routing."

    return RegionalDistributionPlan(
        regions=allocations,
        total_demand_mw=round(national_demand_mw, 1),
        total_allocated_mw=round(total_allocated, 1),
        total_unmet_mw=round(total_unmet, 1),
        total_transmission_cost_usd=round(total_cost, 2),
        overall_fulfillment_pct=round((total_allocated / national_demand_mw) * 100, 1),
        total_station_capacity_mw=total_capacity,
        feasible=True,
        system_recommendation=system_recommendation,
    )
