import pytest
from fastapi.testclient import TestClient
from main import app
from shared.state_schema import SystemState, ConditionSeverity

client = TestClient(app)

def test_emergency_trigger_accident():
    payload = {
        "text": "Huge accident on shahrah e faisal, need ICU immediately",
        "latitude": 24.8607,
        "longitude": 67.0011
    }
    response = client.post("/api/emergency/trigger", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["patient"]["severity"] == ConditionSeverity.CRITICAL.value
    assert data["patient"]["requires_icu"] == True
    assert data["dispatch"]["status"] == "active"

def test_emergency_trigger_stable():
    payload = {
        "text": "minor cut on finger",
        "latitude": 24.8607,
        "longitude": 67.0011
    }
    response = client.post("/api/emergency/trigger", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["patient"]["severity"] == ConditionSeverity.MODERATE.value
    assert data["patient"]["requires_icu"] == False

def test_system_reset():
    response = client.post("/api/emergency/reset")
    assert response.status_code == 200
    assert response.json()["status"] == "reset"
