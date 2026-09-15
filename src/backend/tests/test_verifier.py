import pandas as pd

from backend.agents.verifier import verify_brief
from backend.llm.provider import TemplateNarrationProvider
from backend.tools.anomaly_detection import AnomalyEpisode
from backend.tools.curtailment import minimize_curtailment
from backend.tools.forecasting import forecast_demand
from backend.tools.load_balancing import LoadBalanceConfig, solve_load_balance
from backend.tools.root_cause import RootCauseFinding


def _sample_state() -> dict:
    import numpy as np

    idx = pd.date_range("2024-01-01", periods=24 * 21, freq="h", tz="UTC")
    load = 40000 + 8000 * np.sin((idx.hour.to_numpy() - 6) / 24 * 2 * np.pi)
    series = pd.Series(load, index=idx)
    forecast = forecast_demand(series, horizon_hours=24)

    episode = AnomalyEpisode(
        asset="wind_onshore",
        start=idx[100],
        end=idx[103],
        direction="under",
        duration_hours=4,
        avg_deviation=-0.22,
        peak_deviation=-0.31,
    )
    finding = RootCauseFinding(
        episode=episode,
        category="equipment_or_availability_fault",
        label="Possible equipment or availability fault (isolated to this asset)",
        evidence={},
    )

    demand = [1000, 1000, 1000]
    renewable = [500, 500, 2000]
    config = LoadBalanceConfig(
        dispatchable_capacity_mw=1200, storage_capacity_mwh=1500, storage_max_rate_mw=1000
    )
    load_balance = solve_load_balance(demand, renewable, config)
    curtailment = minimize_curtailment(demand, renewable, config)

    return {
        "forecast": forecast,
        "anomalies": [finding],
        "load_balance": load_balance,
        "curtailment": curtailment,
    }


def test_real_brief_from_template_provider_passes_verification():
    state = _sample_state()
    narrative = TemplateNarrationProvider().narrate(state)
    result = verify_brief(narrative, state)
    assert result.trusted, f"Unexpected unverified numbers: {result.unverified_numbers}"
    assert result.trusted_pool_size > 0


def test_fabricated_number_is_caught():
    state = _sample_state()
    narrative = TemplateNarrationProvider().narrate(state)
    fabricated = narrative + "\n\nNote: total system capacity is 987654 MW."
    result = verify_brief(fabricated, state)
    assert not result.trusted
    assert 987654.0 in result.unverified_numbers


def test_empty_state_yields_no_trusted_numbers():
    result = verify_brief("The forecast peaks at 42000 MW.", {})
    assert not result.trusted
    assert result.trusted_pool_size == 0
