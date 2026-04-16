import pytest
from fastapi.testclient import TestClient
from main import app
from app.graph import VENUE_GRAPH

client = TestClient(app)

def test_stats_endpoint():
    response = client.get("/api/stats") # Using the polling fallback for tests
    assert response.status_code == 200
    data = response.json()
    assert "attendance" in data
    assert "mass_exodus" in data
    assert "heatmap" in data
    assert len(data["heatmap"]) == len(VENUE_GRAPH)
    assert "density" in data["heatmap"][0]

def test_routing_endpoint_standard():
    response = client.post("/api/route", json={
        "start_node": "entrance_north",
        "end_node": "seating_section_a",
        "emergency_mode": False,
        "accessible_mode": False,
        "scenic_mode": False,
        "smart_restroom": False
    })
    assert response.status_code == 200
    data = response.json()
    assert "recommended_route" in data
    assert "confidence_score" in data
    assert "crowd_impact" in data
    assert "estimated_time" in data

def test_routing_endpoint_emergency():
    response = client.post("/api/route", json={
        "start_node": "seating_section_a",
        "end_node": "emergency_exit_west",
        "emergency_mode": True,
        "accessible_mode": False,
        "scenic_mode": False,
        "smart_restroom": False
    })
    assert response.status_code == 200
    data = response.json()
    assert "EVACUATION" in data["reasoning"]
    assert data["confidence_score"] == 99

def test_admin_trigger():
    # Adding mock headers for the new Basic Auth on admin endpoints
    headers = {"Authorization": "Bearer mock-admin-token-123"}
    response = client.post("/api/admin/trigger-congestion?node=concourse_west&severity=3.0", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_mass_exodus():
    headers = {"Authorization": "Bearer mock-admin-token-123"}
    # Turn on exodus
    client.post("/api/admin/exodus?state_val=active", headers=headers)
    # Test routing
    response = client.post("/api/route", json={
        "start_node": "seating_section_a",
        "end_node": "food_court_1",
        "emergency_mode": False,
        "accessible_mode": False,
        "scenic_mode": False,
        "smart_restroom": False
    })
    data = response.json()
    assert "Mass Exodus" in data["reasoning"]
    assert data["target_relocated"] is not None
    # Reset
    client.post("/api/admin/exodus?state_val=inactive", headers=headers)
