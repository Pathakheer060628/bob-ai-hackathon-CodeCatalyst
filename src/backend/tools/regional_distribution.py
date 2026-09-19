"""Regional power distribution: population-weighted demand per region, routed
from the nearest generation station, cost-optimized via linear programming --
plus two simpler, commonly-used allocation heuristics kept alongside it purely
for comparison, so the LP's advantage is a measured result, not an assertion.

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

Three distribution algorithms, in increasing order of sophistication:

  - **Nearest-Only Greedy** (`solve_nearest_greedy`): the naive real-world
    default -- each region draws only from its single nearest hub, largest
    demand served first, no reallocation once that hub is exhausted. Simple
    to reason about, but a saturated nearest hub strands that region even
    when a farther hub has spare capacity.
  - **Proportional Fair-Share** (`solve_proportional_fair_share`): a common
    "fairness" heuristic -- each hub's capacity is split across the regions
    naturally nearest to it, proportional to their demand share, so a
    shortfall is spread evenly rather than one region losing out entirely.
    Still no cross-hub reallocation, so a whole cluster can be short even
    while a neighboring hub sits idle.
  - **Cost-Optimal LP** (`solve_regional_distribution`, the algorithm this
    module actually deploys): a classic transportation-problem linear
    program (scipy HiGHS), solved the same way backend/tools/
    load_balancing.py solves dispatch -- minimize routing cost with an
    always-available "unmet demand" slack at a very high penalty, so the
    solver is never infeasible. It can route across *any* hub-region pair,
    not just the nearest one, so it reallocates surplus capacity from one
    hub to a neighboring hub's shortfall automatically. Because shorter
    routes are cheaper, it still prefers the nearest hub first -- it just
    isn't *stuck* with that choice the way the other two are.

`compare_distribution_algorithms` runs all three over the same demand
snapshot and reports fulfillment/cost/worst-region numbers side by side.
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
    algorithm: str = "lp_optimal"
    regions: list[RegionAllocation] = field(default_factory=list)
    total_demand_mw: float = 0.0
    total_allocated_mw: float = 0.0
    total_unmet_mw: float = 0.0
    total_transmission_cost_usd: float = 0.0
    overall_fulfillment_pct: float = 100.0
    total_station_capacity_mw: float = 0.0
    feasible: bool = True
    system_recommendation: str = ""


@dataclass
class AlgorithmComparison:
    algorithm: str
    label: str
    overall_fulfillment_pct: float
    total_unmet_mw: float
    total_transmission_cost_usd: float
    worst_region_fulfillment_pct: float


def _setup(national_demand_mw: float):
    if national_demand_mw <= 0:
        raise ValueError("national_demand_mw must be positive")
    demand = [national_demand_mw * (r.population / TOTAL_POPULATION) for r in REGIONS]
    distances = [[haversine_km(s.lat, s.lon, r.lat, r.lon) for r in REGIONS] for s in STATIONS]
    nearest_idx = [min(range(len(STATIONS)), key=lambda i: distances[i][j]) for j in range(len(REGIONS))]
    return demand, distances, nearest_idx


def _region_recommendation(region: Region, station: Station, distance_km: float, unmet_mw: float) -> str:
    if unmet_mw <= 0.5:
        return f"Need fully met from {station.name} ({distance_km:.0f} km)."
    return (
        f"Shortfall of {unmet_mw:,.0f} MW -- nearest station ({station.name}) is at capacity. "
        f"Recommend demand-response/load-shedding for this shortfall, or new dispatchable/storage capacity "
        f"sited closer to {region.name} to reduce reliance on longer, costlier routes."
    )


def _finalize(
    algorithm: str,
    national_demand_mw: float,
    demand: list[float],
    distances: list[list[float]],
    nearest_idx: list[int],
    allocated_mw: list[float],
) -> RegionalDistributionPlan:
    """Shared tail-end: build RegionAllocation rows + summary stats from a
    per-region allocated-MW vector, regardless of which algorithm produced it.
    """
    allocations: list[RegionAllocation] = []
    total_allocated = total_unmet = total_cost = 0.0

    for j, region in enumerate(REGIONS):
        alloc = allocated_mw[j]
        unmet = max(0.0, demand[j] - alloc)
        nearest_i = nearest_idx[j]
        station = STATIONS[nearest_i]
        cost = alloc * distances[nearest_i][j] * COST_PER_MW_KM

        total_allocated += alloc
        total_unmet += unmet
        total_cost += cost

        allocations.append(
            RegionAllocation(
                region=region.name,
                population=region.population,
                demand_mw=round(demand[j], 1),
                nearest_station=station.name,
                nearest_station_distance_km=round(distances[nearest_i][j], 1),
                allocated_mw=round(alloc, 1),
                unmet_mw=round(unmet, 1),
                fulfillment_pct=round((alloc / demand[j]) * 100, 1) if demand[j] > 0 else 100.0,
                transmission_cost_usd=round(cost, 2),
                recommended_action=_region_recommendation(region, station, distances[nearest_i][j], unmet),
            )
        )

    allocations.sort(key=lambda a: a.unmet_mw, reverse=True)
    total_capacity = sum(s.capacity_mw for s in STATIONS)

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
        system_recommendation = "All regional demand met within station capacity at this algorithm's routing."

    return RegionalDistributionPlan(
        algorithm=algorithm,
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


def solve_nearest_greedy(national_demand_mw: float) -> RegionalDistributionPlan:
    """Naive baseline: each region draws only from its own nearest hub,
    largest-demand region served first, no reallocation once that hub runs
    out. Represents "today's typical simple dispatch order" -- no algorithm
    is running here, just first-come-first-served against a fixed nearest
    assignment.
    """
    demand, distances, nearest_idx = _setup(national_demand_mw)
    remaining = {i: s.capacity_mw for i, s in enumerate(STATIONS)}
    allocated = [0.0] * len(REGIONS)

    order = sorted(range(len(REGIONS)), key=lambda j: demand[j], reverse=True)
    for j in order:
        i = nearest_idx[j]
        take = min(demand[j], remaining[i])
        allocated[j] = take
        remaining[i] -= take

    return _finalize("nearest_greedy", national_demand_mw, demand, distances, nearest_idx, allocated)


def solve_proportional_fair_share(national_demand_mw: float) -> RegionalDistributionPlan:
    """Common "fairness" heuristic: cluster regions by nearest hub, then split
    that hub's capacity across its cluster proportional to each region's
    demand share -- so a shortfall is spread evenly across a cluster instead
    of one region losing out entirely. Still no cross-hub reallocation: a
    whole cluster can be short while a neighboring hub has spare capacity.
    """
    demand, distances, nearest_idx = _setup(national_demand_mw)
    clusters: dict[int, list[int]] = {}
    for j, i in enumerate(nearest_idx):
        clusters.setdefault(i, []).append(j)

    allocated = [0.0] * len(REGIONS)
    for i, station in enumerate(STATIONS):
        members = clusters.get(i, [])
        if not members:
            continue
        cluster_demand = sum(demand[j] for j in members)
        if cluster_demand <= 0:
            continue
        scale = min(1.0, station.capacity_mw / cluster_demand)
        for j in members:
            allocated[j] = demand[j] * scale

    return _finalize("proportional_fair_share", national_demand_mw, demand, distances, nearest_idx, allocated)


def solve_regional_distribution(national_demand_mw: float) -> RegionalDistributionPlan:
    """Cost-optimal transportation LP -- the algorithm this module actually
    deploys. Unlike the two heuristics above, it can route any hub to any
    region, so it automatically shifts surplus capacity from an underused
    hub to a neighboring hub's shortfall; it just prefers the nearest hub
    whenever that's also cheapest, which it almost always is.
    """
    demand, distances, nearest_idx = _setup(national_demand_mw)
    n_stations, n_regions = len(STATIONS), len(REGIONS)
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

    if not result.success:
        # Should not happen given the unmet slack, but stay honest if the solver
        # itself fails rather than silently returning a fabricated plan.
        total_capacity = sum(s.capacity_mw for s in STATIONS)
        return RegionalDistributionPlan(
            algorithm="lp_optimal",
            regions=[],
            total_demand_mw=round(national_demand_mw, 1),
            total_station_capacity_mw=total_capacity,
            feasible=False,
            system_recommendation="Solver failed to find any allocation -- check station/region reference data.",
        )

    x = result.x
    allocated = [sum(x[x_idx(i, j)] for i in range(n_stations)) for j in range(n_regions)]

    return _finalize("lp_optimal", national_demand_mw, demand, distances, nearest_idx, allocated)


ALGORITHMS = {
    "nearest_greedy": ("Nearest-Only Greedy (naive baseline)", solve_nearest_greedy),
    "proportional_fair_share": ("Proportional Fair-Share (per-cluster, no reallocation)", solve_proportional_fair_share),
    "lp_optimal": ("Cost-Optimal LP (deployed algorithm)", solve_regional_distribution),
}


def compare_distribution_algorithms(national_demand_mw: float) -> list[AlgorithmComparison]:
    """Runs all three algorithms over the same demand snapshot so the LP's
    advantage is a measured result (fulfillment %, cost, worst-region outcome)
    rather than an assertion. Order matches ALGORITHMS (naive -> deployed).
    """
    comparisons = []
    for key, (label, solver) in ALGORITHMS.items():
        plan = solver(national_demand_mw)
        worst = min((r.fulfillment_pct for r in plan.regions), default=100.0)
        comparisons.append(
            AlgorithmComparison(
                algorithm=key,
                label=label,
                overall_fulfillment_pct=plan.overall_fulfillment_pct,
                total_unmet_mw=plan.total_unmet_mw,
                total_transmission_cost_usd=plan.total_transmission_cost_usd,
                worst_region_fulfillment_pct=round(worst, 1),
            )
        )
    return comparisons
