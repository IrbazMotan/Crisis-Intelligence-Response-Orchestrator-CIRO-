"""
=============================================================
CIRO — Automated API Integration Wrapper Verification Suite
=============================================================
Launches the FastAPI server in the background, triggers requests
from client device mocks, queries dynamic status telemetry,
tests the critical "all hospitals occupied" fallback warning,
and ensures complete reliability.
=============================================================
"""

import subprocess
import time
import requests
import os
import json
from run_simulation import reset_registry

URL_BASE = "http://127.0.0.1:8000"

def test_api_wrapper():
    print("=" * 80)
    print("           CIRO EMERGENCY RESCUE SYSTEM - API WRAPPER INTEGRATION TEST")
    print("=" * 80)

    # 1. Reset resource counts
    reset_registry()

    # 2. Start Uvicorn FastAPI Server in background
    print("\n[Server] Booting Uvicorn backend server on http://127.0.0.1:8000 ...")
    server_process = subprocess.Popen(
        ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
        cwd=os.path.dirname(__file__),
        shell=True
    )
    
    # Wait for server to bind
    time.sleep(3.0)

    try:
        # Test endpoint: GET /
        print("\n[Test 1] Querying base health check endpoint...")
        res_health = requests.get(f"{URL_BASE}/")
        print(f"  Response Code : {res_health.status_code}")
        print(f"  Response JSON : {res_health.json()}")
        assert res_health.status_code == 200

        # Test endpoint: POST /api/emergency/trigger (Successful dispatch)
        print("\n[Test 2] POST /api/emergency/trigger - Direct device trigger with location pin...")
        payload = {
            "text": "Critical accident near Gulshan, chest trauma",
            "latitude": 24.9215,
            "longitude": 67.0908
        }
        res_trigger = requests.post(f"{URL_BASE}/api/emergency/trigger", json=payload)
        print(f"  Response Code : {res_trigger.status_code}")
        resp_json = res_trigger.json()
        print(f"  Incident ID   : {resp_json.get('incident_id')}")
        print(f"  Status        : {resp_json.get('status').upper()}")
        print(f"  Assigned Amb  : {resp_json.get('assigned_ambulance')}")
        print(f"  Assigned Hosp : {resp_json.get('assigned_hospital')}")
        assert res_trigger.status_code == 201
        assert resp_json.get("success") is True

        incident_id = resp_json.get("incident_id")

        # Test endpoint: GET /api/emergency/status/:id
        print(f"\n[Test 3] GET /api/emergency/status/{incident_id} - Real-time client status lookup...")
        res_status = requests.get(f"{URL_BASE}/api/emergency/status/{incident_id}")
        print(f"  Response Code : {res_status.status_code}")
        status_json = res_status.json()
        print(f"  Patient Status: {status_json.get('patient_status').upper()}")
        print(f"  Ambulance GPS : {status_json.get('ambulance_telemetry', {}).get('current_coordinates')}")
        print(f"  Hospital name : {status_json.get('hospital_telemetry', {}).get('name')}")
        print(f"  Filtered Trace Logs count: {len(status_json.get('trace_logs', []))}")
        assert res_status.status_code == 200

        # Test endpoint: POST /api/emergency/tick - Live movement step
        print("\n[Test 4] POST /api/emergency/tick - Driving responder coordinates dynamic updates...")
        res_tick = requests.post(f"{URL_BASE}/api/emergency/tick")
        print(f"  Response Code : {res_tick.status_code}")
        tick_json = res_tick.json()
        print(f"  Active Responders : {tick_json.get('active_responders')}")
        print(f"  Movement telemetry: {tick_json.get('telemetry')}")
        assert res_tick.status_code == 200

        # Test endpoint: Triggering Critical "All Occupied" Triage Warning State
        # Overwrite database to 0 resources to test error fallback warning
        print("\n[Test 5] Simulating All Hospitals Occupied - Triggering Fallback Warning Logic...")
        
        # Override mock database to zero capacity
        db_path = os.path.join(os.path.dirname(__file__), "data", "hospitals.json")
        with open(db_path, "r") as f:
            pristine_db = json.load(f)
            
        empty_db = []
        for h in pristine_db:
            h_copy = h.copy()
            h_copy["available_beds"] = 0
            h_copy["icu_beds"] = 0
            h_copy["ventilators"] = 0
            empty_db.append(h_copy)
            
        with open(db_path, "w") as f:
            json.dump(empty_db, f, indent=2)

        # Reset active server session state to read the new zeroed registry
        requests.post(f"{URL_BASE}/api/emergency/reset")

        # Send a fresh incident trigger
        empty_payload = {
            "text": "Trauma chest wound at Clifton, critical condition",
            "latitude": 24.8136,
            "longitude": 67.0296
        }
        res_empty = requests.post(f"{URL_BASE}/api/emergency/trigger", json=empty_payload)
        print(f"  Response Code : {res_empty.status_code}")
        empty_json = res_empty.json()
        print(f"  Success       : {empty_json.get('success')}")
        print(f"  Status        : {empty_json.get('status').upper()}")
        print(f"  Warning Msg   : {empty_json.get('warning')}")
        
        assert empty_json.get("success") is False
        assert empty_json.get("status") == "warning"
        assert "No available hospital beds found" in empty_json.get("warning")

        # Query GET /api/emergency/status/:id for the warning incident
        warn_id = empty_json.get("incident_id")
        res_warn_status = requests.get(f"{URL_BASE}/api/emergency/status/{warn_id}")
        print(f"\n[Test 6] GET /api/emergency/status/{warn_id} for warning incident...")
        print(f"  Response Code : {res_warn_status.status_code}")
        warn_status_json = res_warn_status.json()
        print(f"  Patient Status: {warn_status_json.get('patient_status').upper()}")
        print(f"  Ambulance GPS : {warn_status_json.get('ambulance_telemetry')}")
        print(f"  Hospital name : {warn_status_json.get('hospital_telemetry')}")
        print(f"  Warning State : {warn_status_json.get('warning')}")
        assert warn_status_json.get("success") is False
        assert warn_status_json.get("status") == "warning"

        # Restore hospital database
        with open(db_path, "w") as f:
            json.dump(pristine_db, f, indent=2)

        # Reset active server session state to read restored registry
        requests.post(f"{URL_BASE}/api/emergency/reset")

        # Test endpoint: Weather Fraud Security Check
        print("\n[Test 7] Triggering extreme heatwave (under 38C) to check Fraud Rejection Status...")
        fraud_payload = {
            "text": "heatwave near Clifton, patient dehydrating",
            "latitude": 24.8136,
            "longitude": 67.0296
        }
        res_fraud = requests.post(f"{URL_BASE}/api/emergency/trigger", json=fraud_payload)
        print(f"  Response Code : {res_fraud.status_code}")
        fraud_json = res_fraud.json()
        print(f"  Success       : {fraud_json.get('success')}")
        print(f"  Status        : {fraud_json.get('status').upper()}")
        print(f"  Warning Msg   : {fraud_json.get('warning')}")
        print(f"  Patient Status: {fraud_json.get('patient_status')}")
        
        assert fraud_json.get("success") is False
        assert fraud_json.get("status") == "rejected"
        assert fraud_json.get("patient_status") == "rejected"
        assert "SECURITY WARNING" in fraud_json.get("warning")

        # Query GET /api/emergency/status/:id for the fraud incident
        fraud_id = fraud_json.get("incident_id")
        res_fraud_status = requests.get(f"{URL_BASE}/api/emergency/status/{fraud_id}")
        print(f"\n[Test 8] GET /api/emergency/status/{fraud_id} for fraud incident...")
        print(f"  Response Code : {res_fraud_status.status_code}")
        fraud_status_json = res_fraud_status.json()
        print(f"  Patient Status: {fraud_status_json.get('patient_status').upper()}")
        print(f"  Warning State : {fraud_status_json.get('warning')}")
        assert fraud_status_json.get("success") is False
        assert fraud_status_json.get("status") == "rejected"
        assert fraud_status_json.get("patient_status") == "rejected"
        assert "SECURITY WARNING" in fraud_status_json.get("warning")

        print("\n" + "=" * 80)
        print("          ALL APIwrapper INTEGRATION TESTS PASSED TRIUMPHANTLY!")
        print("=" * 80)

    finally:
        # Gracefully shut down background Uvicorn server process
        print("\n[Server] Terminating Uvicorn server process gracefully...")
        server_process.terminate()
        server_process.wait()
        print("[Server] Server process terminated.")

if __name__ == "__main__":
    test_api_wrapper()
