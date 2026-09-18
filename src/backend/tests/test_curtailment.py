from backend.tools.curtailment import minimize_curtailment
from backend.tools.load_balancing import LoadBalanceConfig


def test_optimized_plan_curtails_no_more_than_baseline():
    demand = [500, 500, 500, 500]
    renewable = [500, 500, 2200, 500]
    config = LoadBalanceConfig(
        dispatchable_capacity_mw=1000,
        storage_capacity_mwh=2000,
        storage_max_rate_mw=1500,
        storage_efficiency=0.9,
        max_demand_response_fraction=0.1,
    )
    plan = minimize_curtailment(demand, renewable, config)
    assert plan.baseline.feasible and plan.optimized.feasible
    assert plan.optimized_curtailed_mwh <= plan.baseline_curtailed_mwh
    assert plan.curtailment_avoided_mwh >= 0


def test_reduction_pct_matches_avoided_mwh():
    demand = [500, 500, 500]
    renewable = [500, 500, 2000]
    config = LoadBalanceConfig(
        dispatchable_capacity_mw=1000, storage_capacity_mwh=1500, storage_max_rate_mw=1000
    )
    plan = minimize_curtailment(demand, renewable, config)
    expected_pct = round(
        (plan.curtailment_avoided_mwh / plan.baseline_curtailed_mwh) * 100, 1
    )
    assert plan.curtailment_reduction_pct == expected_pct


def test_no_baseline_curtailment_gives_zero_pct():
    demand = [2000, 2000]
    renewable = [200, 300]
    config = LoadBalanceConfig(dispatchable_capacity_mw=3000)
    plan = minimize_curtailment(demand, renewable, config)
    assert plan.baseline_curtailed_mwh == 0.0
    assert plan.curtailment_reduction_pct == 0.0


def test_baseline_feasible_with_nonzero_initial_soc():
    """Regression test: a nonzero storage_initial_soc_mwh on the input config must not
    make the baseline (zero-storage) LP infeasible. The baseline zeroes out storage
    capacity/rate to represent "no flexibility", so its initial SOC must be zeroed too
    -- otherwise the SOC balance equation demands soc[0] == storage_initial_soc_mwh
    while the SOC bound is fixed at [0, 0], which is unsatisfiable and silently
    reported curtailment_avoided_mwh as 0 (or negative once the optimized plan
    curtails anything)."""
    demand = [500, 500, 500, 500]
    renewable = [500, 500, 2200, 500]
    config = LoadBalanceConfig(
        dispatchable_capacity_mw=1000,
        storage_capacity_mwh=2000,
        storage_max_rate_mw=1500,
        storage_efficiency=0.9,
        storage_initial_soc_mwh=800,
        max_demand_response_fraction=0.1,
    )
    plan = minimize_curtailment(demand, renewable, config)
    assert plan.baseline.feasible
    assert plan.curtailment_avoided_mwh >= 0


def test_recommended_actions_only_include_active_hours():
    demand = [500, 500, 500]
    renewable = [500, 500, 2000]
    config = LoadBalanceConfig(
        dispatchable_capacity_mw=1000, storage_capacity_mwh=1500, storage_max_rate_mw=1000
    )
    plan = minimize_curtailment(demand, renewable, config)
    for action in plan.recommended_actions:
        assert action.shed_mw > 0.01 or action.discharge_mw > 0.01 or action.charge_mw > 0.01
