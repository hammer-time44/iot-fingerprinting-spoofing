"""
API and WebSocket tests for Network Defense Lab.
Tests every REST endpoint and WebSocket connection smoke test.
"""

import pytest
from fastapi.testclient import TestClient
from network_guard.backend.main import app, sim_engine

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "service" in data

def test_model_info_endpoint():
    res = client.get("/model/info")
    assert res.status_code == 200
    data = res.json()
    assert "classes" in data
    assert len(data["classes"]) == 5
    assert data["tau"] == sim_engine.tau
    assert "feature_names" in data
    assert len(data["feature_names"]) == 13

def test_topology_endpoint():
    res = client.get("/topology")
    assert res.status_code == 200
    data = res.json()
    assert "gateway" in data
    assert "home_lan" in data
    assert len(data["home_lan"]["hosts"]) == 5
    assert "attacker_net" in data

def test_registry_endpoint():
    res = client.get("/registry")
    assert res.status_code == 200
    data = res.json()
    assert "host-echo" in data
    assert data["host-echo"]["claimed_device"] == "AmazonEcho"

def test_hosts_endpoint():
    res = client.get("/hosts")
    assert res.status_code == 200
    data = res.json()
    assert "hosts" in data
    assert len(data["hosts"]) >= 5

def test_simulation_lifecycle():
    # Start simulation
    res_start = client.post("/sim/start", json={
        "scenario": "IMPERSONATION",
        "params": {"source_device": "SamsungCamera", "claimed_device": "AmazonEcho"},
        "speed": 2.0
    })
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "started"

    # Check hosts after start
    res_hosts = client.get("/hosts")
    assert res_hosts.status_code == 200
    assert "host-attacker" in res_hosts.json()["hosts"]

    # Speed change
    res_speed = client.post("/sim/speed", json={"speed": 4.0})
    assert res_speed.status_code == 200
    assert res_speed.json()["speed"] == 4.0

    # Stop simulation
    res_stop = client.post("/sim/stop")
    assert res_stop.status_code == 200
    assert res_stop.json()["status"] == "stopped"

    # Reset simulation
    res_reset = client.post("/sim/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "reset"

def test_tau_configuration():
    res = client.post("/config/tau", json={"tau": 0.88})
    assert res.status_code == 200
    assert res.json()["tau"] == 0.88
    # Reset back to 0.84
    client.post("/config/tau", json={"tau": 0.84})

def test_events_endpoint():
    # Trigger a tick to generate events
    sim_engine.tick()
    res = client.get("/events?limit=50")
    assert res.status_code == 200
    assert "events" in res.json()

    # CSV export
    res_csv = client.get("/events?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]

def test_benchmark_results_endpoint():
    res = client.get("/benchmark/results")
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "mimicry_curve" in data

def test_report_endpoint():
    res = client.get("/report")
    assert res.status_code == 200
    data = res.json()
    assert "gateway" in data
    assert "hosts" in data

def test_websocket_smoke():
    with client.websocket_connect("/ws/events") as ws:
        # Should receive initial SNAPSHOT message
        msg = ws.receive_json()
        assert msg["type"] == "SNAPSHOT"
        assert "hosts" in msg
        assert len(msg["hosts"]) >= 5

