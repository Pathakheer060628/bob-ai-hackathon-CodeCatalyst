import json

from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def test_dataset_info():
    resp = client.get("/api/dataset/info")
    assert resp.status_code == 200
    body = resp.json()
    assert "start" in body and "end" in body


def test_create_run_returns_pending_id():
    resp = client.post("/api/runs", json={"window_end": "2019-06-30T23:00:00", "lookback_days": 30, "horizon_hours": 24})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert len(body["run_id"]) > 0


def test_create_run_rejects_out_of_range_window():
    resp = client.post("/api/runs", json={"window_end": "2050-01-01T00:00:00", "lookback_days": 30, "horizon_hours": 24})
    assert resp.status_code == 400


def test_full_run_lifecycle_via_stream_then_pdf():
    create_resp = client.post(
        "/api/runs", json={"window_end": "2019-06-30T23:00:00", "lookback_days": 30, "horizon_hours": 24}
    )
    run_id = create_resp.json()["run_id"]

    events = []
    with client.stream("GET", f"/api/runs/{run_id}/stream") as stream_resp:
        assert stream_resp.status_code == 200
        event_type = None
        for line in stream_resp.iter_lines():
            if not line:
                continue
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
                events.append((event_type, data))

    result_events = [d for t, d in events if t == "result"]
    assert len(result_events) == 1
    result = result_events[0]
    assert result["verification"]["trusted"]
    assert result["curtailment"]["curtailment_avoided_mwh"] >= 0

    status_resp = client.get(f"/api/runs/{run_id}")
    assert status_resp.json()["status"] == "done"

    pdf_resp = client.get(f"/api/runs/{run_id}/report.pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content[:4] == b"%PDF"


def test_pdf_before_run_complete_returns_409():
    create_resp = client.post(
        "/api/runs", json={"window_end": "2019-06-30T23:00:00", "lookback_days": 30, "horizon_hours": 24}
    )
    run_id = create_resp.json()["run_id"]
    pdf_resp = client.get(f"/api/runs/{run_id}/report.pdf")
    assert pdf_resp.status_code == 409


def test_unknown_run_id_returns_404():
    assert client.get("/api/runs/doesnotexist").status_code == 404
    assert client.get("/api/runs/doesnotexist/report.pdf").status_code == 404
