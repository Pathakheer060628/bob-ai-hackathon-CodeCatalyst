import pytest

from backend.tools.load_balancing import LoadBalanceConfig, solve_load_balance


def test_balance_holds_every_hour_when_feasible():
    demand = [1000, 1200, 900, 1500]
    renewable = [400, 300, 800, 200]
    config = LoadBalanceConfig(dispatchable_capacity_mw=2000)
    plan = solve_load_balance(demand, renewable, config)
    assert plan.feasible
    for h in plan.hours:
        supply = h.dispatch_mw + h.discharge_mw - h.charge_mw - h.curtail_mw + h.shed_mw + h.unmet_mw
        assert supply == pytest.approx(h.demand_mw - h.renewable_mw, abs=0.5)


def test_no_curtailment_when_renewable_never_exceeds_demand():
    # dispatch can always ramp down to 0 and cover the remaining gap, so as
    # long as renewable output never exceeds demand there is no surplus to curtail
    demand = [1000, 1000, 1400]
    renewable = [200, 200, 900]
    config = LoadBalanceConfig(dispatchable_capacity_mw=2000)
    plan = solve_load_balance(demand, renewable, config)
    assert plan.feasible
    assert plan.total_curtailed_mwh == 0.0


def test_curtailment_needed_when_renewable_exceeds_demand_and_no_storage():
    demand = [500, 500, 500]
    renewable = [500, 500, 2000]  # hour 2 has 1500 MW of unabsorbable oversupply
    config = LoadBalanceConfig(dispatchable_capacity_mw=1000, storage_max_rate_mw=0, max_demand_response_fraction=0)
    plan = solve_load_balance(demand, renewable, config)
    assert plan.feasible
    assert plan.total_curtailed_mwh == pytest.approx(1500.0, abs=0.5)


def test_storage_absorbs_oversupply_instead_of_curtailing():
    demand = [500, 500, 500]
    renewable = [500, 500, 2000]
    config = LoadBalanceConfig(
        dispatchable_capacity_mw=1000,
        storage_capacity_mwh=2000,
        storage_max_rate_mw=1500,
        storage_efficiency=1.0,
    )
    plan = solve_load_balance(demand, renewable, config)
    assert plan.feasible
    assert plan.total_curtailed_mwh < 1500.0
    assert any(h.charge_mw > 0 for h in plan.hours)


def test_dispatch_covers_demand_when_no_renewable():
    demand = [800, 900]
    renewable = [0, 0]
    config = LoadBalanceConfig(dispatchable_capacity_mw=1200)
    plan = solve_load_balance(demand, renewable, config)
    assert plan.feasible
    assert plan.total_unmet_mwh == 0.0
    for h, d in zip(plan.hours, demand):
        assert h.dispatch_mw == pytest.approx(d, abs=0.5)


def test_unmet_demand_when_capacity_insufficient():
    demand = [5000]
    renewable = [0]
    config = LoadBalanceConfig(dispatchable_capacity_mw=1000)
    plan = solve_load_balance(demand, renewable, config)
    assert plan.feasible
    assert plan.total_unmet_mwh == pytest.approx(4000.0, abs=0.5)


def test_mismatched_lengths_raise():
    with pytest.raises(ValueError):
        solve_load_balance([1, 2], [1], LoadBalanceConfig(dispatchable_capacity_mw=100))
