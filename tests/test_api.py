import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_endpoint():
    """Requirement 11: GET /health returns 200 and {'status': 'ok'}"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_list_runs_includes_seed():
    """Requirement 11: GET /api/runs returns 200 and includes sbx-seeddemo1"""
    response = client.get("/api/runs")
    assert response.status_code == 200
    runs = response.json()
    assert isinstance(runs, list)
    sandbox_names = [r["sandbox_name"] for r in runs]
    assert "sbx-seeddemo1" in sandbox_names

def test_post_run_success():
    """Requirement 11: POST /api/runs with valid body returns 201 and stored object"""
    payload = {
        "run_id": "test-run-valid-01",
        "sandbox_name": "sbx-testvalid123",
        "problem_id": "test-problem-01",
        "state": "running",
        "execution_target": "celesto_sandbox"
    }
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["run_id"] == "test-run-valid-01"
    assert data["sandbox_name"] == "sbx-testvalid123"
    assert data["execution_target"] == "celesto_sandbox"

def test_post_run_rejects_host_target():
    """Requirement 11: POST execution_target host and expect 400"""
    payload = {
        "run_id": "test-run-host-01",
        "sandbox_name": "sbx-testhost123",
        "problem_id": "test-problem-01",
        "state": "running",
        "execution_target": "host"
    }
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 400

def test_post_run_rejects_invalid_sandbox_name():
    """Requirement 11: Invalid sandbox_name returns 400"""
    payload = {
        "run_id": "test-run-bad-name",
        "sandbox_name": "bad-name",  # does not match sbx-[a-z0-9]{8,}
        "problem_id": "test-problem-01",
        "state": "running",
        "execution_target": "celesto_sandbox"
    }
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 400

def test_post_run_rejects_invalid_state():
    """Requirement 11: Unknown state returns 400"""
    payload = {
        "run_id": "test-run-bad-state",
        "sandbox_name": "sbx-validname123",
        "problem_id": "test-problem-01",
        "state": "unknown_state",
        "execution_target": "celesto_sandbox"
    }
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 400
