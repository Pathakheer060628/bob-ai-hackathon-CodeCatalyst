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
    assert nodes_seen == ["forecast", "anomalies", "load_balance", "curtailment", "narrate", "verify"]
