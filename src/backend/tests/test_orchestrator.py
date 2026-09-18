import pandas as pd

from backend.agents.orchestrator import PipelineRequest, run_pipeline, stream_pipeline
from backend.data.loader import load_grid_data


def _sample_request(days: int = 30) -> PipelineRequest:
    full_history = load_grid_data()
    window_end = pd.Timestamp("2019-06-30 23:00:00", tz="UTC")
    window_start = window_end - pd.Timedelta(days=days)
    history = full_history.loc[window_start:window_end]
    return PipelineRequest(history=history, full_history=full_history, horizon_hours=24)


def test_pipeline_runs_end_to_end_on_real_data():
    result = run_pipeline(_sample_request())
    assert result["forecast"] is not None
    assert len(result["forecast"].hourly) == 24
    assert result["load_balance"].feasible
    assert result["curtailment"] is not None
    assert result["narrative"]
    assert result["verification"].trusted, result["verification"].unverified_numbers


def test_pipeline_progress_log_covers_every_stage():
    result = run_pipeline(_sample_request())
    log_text = " ".join(result["progress_log"])
    assert "Forecast complete" in log_text
    assert "Load-balance plan solved" in log_text
    assert "Curtailment plan" in log_text
    assert "narrated by" in log_text
    assert "Verifier" in log_text


def test_stream_pipeline_yields_all_nodes_in_order():
    nodes_seen = [name for name, _ in stream_pipeline(_sample_request())]
    assert nodes_seen == [
        "data_quality",
        "forecast",
        "anomalies",
        "load_balance",
        "curtailment",
        "facts",
        "narrate",
        "verify",
    ]


def test_pipeline_result_includes_facts_and_manifest():
    result = run_pipeline(_sample_request())
    assert result["data_quality"].hard_fail is False
    assert result["facts"], "expected a non-empty fact ledger"
    assert result["manifest"]["model_versions"]
    assert result["forecast_backtest"] is not None


def test_scenario_scales_forecast_and_is_labeled_simulated():
    from backend.agents.orchestrator import ScenarioConfig

    request = _sample_request()
    baseline = run_pipeline(request).copy()

    scenario_request = _sample_request()
    scenario_request.scenario = ScenarioConfig(scenario_id="scn_test", renewable_scale=2.5, demand_scale=1.0)
    scenario_result = run_pipeline(scenario_request)

    baseline_peak = baseline["forecast"].peak.forecast_mw
    scenario_peak = scenario_result["forecast"].peak.forecast_mw
    assert scenario_peak == baseline_peak  # demand untouched

    baseline_renewable_total = sum(baseline["renewable_forecast_mw"])
    scenario_renewable_total = sum(scenario_result["renewable_forecast_mw"])
    assert scenario_renewable_total > baseline_renewable_total

    log_text = " ".join(scenario_result["progress_log"])
    assert "SIMULATED SCENARIO" in log_text


def test_hard_data_quality_failure_blocks_before_optimization():
    full_history = load_grid_data()
    window_end = pd.Timestamp("2019-06-30 23:00:00", tz="UTC")
    window_start = window_end - pd.Timedelta(days=3)  # under the 1-week minimum -> hard fail
    history = full_history.loc[window_start:window_end]
    request = PipelineRequest(history=history, full_history=full_history, horizon_hours=24)

    result = run_pipeline(request)
    assert result["data_quality"].hard_fail
    assert "forecast" not in result
    assert "narrative" not in result
