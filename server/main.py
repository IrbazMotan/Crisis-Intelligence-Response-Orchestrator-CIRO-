"""
=============================================================
CIRO — FastAPI Entry Point (main.py)
=============================================================
Connects the Google Antigravity emergency multi-agent orchestrator
and live telemetry tracking flow directly to clients.
=============================================================
"""

import os
import json
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.state_schema import PatientStatus, Hospital, AmbulanceState
from agents.orchestrator import CIROOrchestrator
from tools.environment_tools import get_distance

app = FastAPI(
    title="CIRO Mobile API Portal",
    description="FastAPI gateway exposing the Antigravity multi-agent decision loop and telemetry",
    version="1.0.0"
)

# Enable CORS for frontend dashboard connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Orchestrator Singleton
orchestrator = CIROOrchestrator()


# ─────────────────────────────────────────────
# DATABASE ALIGNMENT CONFIGURATION
# ─────────────────────────────────────────────

def align_mock_database(write_file: bool = True):
    """
    Initializes mock databases with varying capacities to match
    the user's scenario constraints precisely.
    """
    db_path = os.path.join(os.path.dirname(__file__), "data", "hospitals.json")
    
    if write_file:
        # 1. Update hospitals database file with pristine mock data
        mock_hospitals = [
            {
                "id": "HOSP-A",
                "name": "Dr. Ruth K.M. Pfau Civil Hospital (Trauma Center)",
                "hospital_type": "Trauma Center",
                "coordinates": [24.8598, 67.0125],
                "available_beds": 25,
                "icu_beds": 2,
                "ventilators": 1,
                "contact_number": "+92-21-99215740",
                "accepts_trauma": True
            },
            {
                "id": "HOSP-B",
                "name": "Aga Khan University Hospital (AKUH)",
                "hospital_type": "Specialized Tertiary & ICU",
                "coordinates": [24.8922, 67.0747],
                "available_beds": 15,
                "icu_beds": 8,
                "ventilators": 4,
                "contact_number": "+92-21-111-911-911",
                "accepts_trauma": True
            },
            {
                "id": "HOSP-C",
                "name": "National Institute of Cardiovascular Diseases (NICVD)",
                "hospital_type": "Specialized Cardiac",
                "coordinates": [24.8508, 67.0390],
                "available_beds": 10,
                "icu_beds": 12,
                "ventilators": 6,
                "contact_number": "+92-21-99201271",
                "accepts_trauma": False
            },
            {
                "id": "HOSP-D",
                "name": "Jinnah Postgraduate Medical Centre (JPMC)",
                "hospital_type": "General & Trauma",
                "coordinates": [24.8519, 67.0427],
                "available_beds": 30,
                "icu_beds": 5,
                "ventilators": 3,
                "contact_number": "+92-21-99201300",
                "accepts_trauma": True
            },
            {
                "id": "HOSP-E",
                "name": "Indus Hospital & Health Network",
                "hospital_type": "General & ICU",
                "coordinates": [24.8231, 67.1189],
                "available_beds": 18,
                "icu_beds": 6,
                "ventilators": 2,
                "contact_number": "+92-21-111-111-880",
                "accepts_trauma": True
            }
        ]
        with open(db_path, "w") as f:
            json.dump(mock_hospitals, f, indent=2)

    # 2. Overwrite in-memory state hospitals by reading current file contents
    with open(db_path, "r") as f:
        hospitals_data = json.load(f)

    orchestrator.state.hospitals = [
        Hospital(
            id=h["id"],
            name=h["name"],
            hospital_type=h["hospital_type"],
            coordinates=tuple(h["coordinates"]),
            available_beds=h["available_beds"],
            icu_beds=h["icu_beds"],
            ventilators=h["ventilators"],
            contact_number=h["contact_number"],
            accepts_trauma=h["accepts_trauma"]
        ) for h in hospitals_data
    ]

    # 3. Align in-memory ambulance responders exactly
    orchestrator.state.ambulances = [
        AmbulanceState(id="AMB-01", current_coordinates=(24.8607, 67.0011), is_available=True),
        AmbulanceState(id="AMB-02", current_coordinates=(24.9120, 67.0780), is_available=True),
        AmbulanceState(id="AMB-03", current_coordinates=(24.8700, 67.0500), is_available=False)
    ]

# Align registries on server bootstrap
align_mock_database(write_file=True)

from agents.crisis_intelligence_agent import CrisisIntelligenceAgent

# Crisis Intelligence Agent (shares orchestrator system state)
crisis_agent = CrisisIntelligenceAgent(orchestrator.state)


# ─────────────────────────────────────────────
# REQUEST PYLON SCHEMA
# ─────────────────────────────────────────────

class TriggerRequest(BaseModel):
    text: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CrisisAnalysisRequest(BaseModel):
    social_posts: List[str]
    city: Optional[str] = "Karachi"
    include_weather: Optional[bool] = True
    include_traffic: Optional[bool] = True


# ─────────────────────────────────────────────
# SERVER ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/")
def get_root():
    return {
        "status": "healthy",
        "system": "CIRO FastAPI Multi-Agent Engine",
        "hospitals_count": len(orchestrator.state.hospitals),
        "ambulances_count": len(orchestrator.state.ambulances)
    }


@app.post("/api/crisis/analyze")
def analyze_crisis_signals(payload: CrisisAnalysisRequest):
    """
    POST /api/crisis/analyze
    Ingests multi-source signals (social media posts, weather, traffic),
    runs the CrisisIntelligenceAgent pipeline, and returns structured
    crisis detection results with action plans and simulated execution.
    Supports English + Urdu + Roman-Urdu text inputs.
    """
    # Reinitialize agent logs for fresh run
    crisis_agent.state.event_log = []

    result = crisis_agent.analyze_signals(
        social_posts=payload.social_posts,
        city=payload.city or "Karachi",
        include_weather=payload.include_weather,
        include_traffic=payload.include_traffic
    )

    # Attach trace logs
    result["trace_logs"] = [
        entry for entry in orchestrator.state.event_log
        if entry.get("agent") == "CrisisIntelligenceAgent"
    ]

    return result




@app.post("/api/emergency/trigger", status_code=status.HTTP_201_CREATED)
def trigger_emergency(payload: Dict[str, Any]):
    """
    POST /api/emergency/trigger
    Accepts text trigger + direct coordinates pin.
    Exposes dual schema compatibility for text or custom ingestion forms.
    """
    # 1. Detect which schema layout is sent
    if "disaster_type" in payload:
        disaster_type = payload.get("disaster_type") or "accident"
        patient_location = payload.get("patient_location") or "Unknown Landmark"
        requires_icu = payload.get("requires_icu", False)
        requires_ventilator = payload.get("requires_ventilator", False)
        
        trigger_text = f"Disaster Type: {disaster_type}. Location: {patient_location}. Requires ICU: {requires_icu}. Requires Ventilator: {requires_ventilator}"
        
        coords = payload.get("coordinates") or {}
        lat = coords.get("lat")
        lng = coords.get("lng")
    else:
        trigger_text = payload.get("text", "")
        lat = payload.get("latitude")
        lng = payload.get("longitude")

    live_coords = None
    if lat is not None and lng is not None:
        live_coords = (lat, lng)

    # 2. Run orchestrator multi-agent pipeline
    start_log_count = len(orchestrator.state.event_log)
    result = orchestrator.process_trigger(trigger_text, live_coords=live_coords)
    patient_data = result["patient"]
    incident_id = patient_data["id"]

    # Tag all newly added logs with the incident_id
    for i in range(start_log_count, len(orchestrator.state.event_log)):
        orchestrator.state.event_log[i]["incident_id"] = incident_id

    # 3. Override patient request coordinates if coordinates were explicitly sent
    if live_coords:
        patient_req = next((p for p in orchestrator.state.patient_requests if p.id == incident_id), None)
        if patient_req:
            patient_req.location = live_coords
            patient_data["location"] = patient_req.location

    # 4. Handle occupied/no-hospital warning logic/rejected security validation
    if patient_data.get("status") == "rejected":
        return {
            "success": False,
            "incident_id": incident_id,
            "status": "rejected",
            "message": patient_data.get("explanation") or "Security verification failed. Sensor anomaly or coordinates mismatch detected.",
            "warning": patient_data.get("explanation") or "CRITICAL: Security verification failed. Sensor anomaly or coordinates mismatch detected.",
            "patient_status": "rejected",
            "patient_details": patient_data
        }

    if not result["success"]:
        return {
            "success": False,
            "incident_id": incident_id,
            "status": "warning",
            "message": "All mock hospitals are fully occupied. Emergency is registered but pending resource assignment.",
            "warning": "CRITICAL: No available hospital beds found across all regional registries. Patient remains in PENDING queue.",
            "patient_status": PatientStatus.PENDING.value,
            "patient_details": patient_data
        }

    # 5. Success response
    hosp = next((h for h in orchestrator.state.hospitals if h.id == patient_data["assigned_hospital"]), None)
    hosp_name = hosp.name if hosp else "Unknown Hospital"

    return {
        "success": True,
        "incident_id": incident_id,
        "status": "dispatched",
        "message": "Emergency incident dispatched successfully.",
        "assigned_ambulance": patient_data["assigned_ambulance"],
        "assigned_hospital": hosp_name,
        "patient_details": patient_data
    }


@app.get("/api/emergency/status/{incident_id}")
def get_emergency_status(incident_id: str):
    """
    GET /api/emergency/status/{incident_id}
    Streams trace logs, patient status, ambulance telemetry waypoints, and hospital resources.
    """
    # 1. Fetch patient request
    patient = next((p for p in orchestrator.state.patient_requests if p.id == incident_id), None)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found."
        )

    # 2. Fetch specific logs
    incident_logs = [
        log for log in orchestrator.state.event_log 
        if log.get("incident_id") == incident_id or incident_id in log["message"] or incident_id in log.get("agent", "")
    ]

    # 3. Retrieve responder telemetry
    ambulance_telemetry = None
    if patient.assigned_ambulance:
        amb = next((a for a in orchestrator.state.ambulances if a.id == patient.assigned_ambulance), None)
        if amb:
            ambulance_telemetry = {
                "ambulance_id": amb.id,
                "current_coordinates": amb.current_coordinates,
                "is_available": amb.is_available,
                "route_polyline": amb.route_polyline
            }

    # 4. Retrieve target hospital coordinates & resources
    hospital_telemetry = None
    if patient.assigned_hospital:
        hosp = next((h for h in orchestrator.state.hospitals if h.id == patient.assigned_hospital), None)
        if hosp:
            hospital_telemetry = {
                "hospital_id": hosp.id,
                "name": hosp.name,
                "hospital_type": hosp.hospital_type,
                "coordinates": hosp.coordinates,
                "available_beds": hosp.available_beds,
                "icu_beds": hosp.icu_beds,
                "ventilators": hosp.ventilators,
                "contact_number": hosp.contact_number
            }

    # 5. Handle Occupied Rejections Warning / Security Fraud Rejection
    if not patient.assigned_hospital:
        if patient.status == PatientStatus.REJECTED:
            return {
                "success": False,
                "incident_id": incident_id,
                "status": "rejected",
                "message": patient.explanation or "Security verification failed. Sensor anomaly or coordinates mismatch detected.",
                "warning": patient.explanation or "CRITICAL: Security verification failed. Sensor anomaly or coordinates mismatch detected.",
                "patient_status": PatientStatus.REJECTED.value,
                "patient_confidence": patient.confidence,
                "patient_explanation": patient.explanation,
                "patient_severity": patient.severity.value,
                "trace_logs": incident_logs,
                "ambulance_telemetry": None,
                "hospital_telemetry": None
            }
        return {
            "success": False,
            "incident_id": incident_id,
            "status": "warning",
            "message": "No hospital resource assigned. Regional beds exhausted.",
            "warning": "CRITICAL: No available hospital beds found across all regional registries. Patient remains in PENDING queue.",
            "patient_status": patient.status.value,
            "patient_confidence": patient.confidence,
            "patient_explanation": patient.explanation,
            "patient_severity": patient.severity.value,
            "trace_logs": incident_logs,
            "ambulance_telemetry": None,
            "hospital_telemetry": None
        }

    return {
        "success": True,
        "incident_id": incident_id,
        "status": "active",
        "patient_status": patient.status.value,
        "patient_confidence": patient.confidence,
        "patient_explanation": patient.explanation,
        "patient_severity": patient.severity.value,
        "trace_logs": incident_logs,
        "ambulance_telemetry": ambulance_telemetry,
        "hospital_telemetry": hospital_telemetry
    }


@app.post("/api/emergency/tick")
def trigger_telemetry_tick():
    """
    Triggers simulated tick coordinate progression along polylines.
    """
    start_log_count = len(orchestrator.state.event_log)
    telemetry = orchestrator.simulate_tick()
    
    # Tag tick logs with the assigned patient id
    for i in range(start_log_count, len(orchestrator.state.event_log)):
        log_entry = orchestrator.state.event_log[i]
        msg = log_entry["message"]
        for amb in orchestrator.state.ambulances:
            if amb.id in msg and amb.assigned_patient_id:
                log_entry["incident_id"] = amb.assigned_patient_id
                
    return {
        "tick_status": "executed",
        "active_responders": len(telemetry),
        "telemetry": telemetry
    }


@app.post("/api/emergency/arrive_patient")
def arrive_at_patient():
    """
    Instantly teleports active ambulance to the patient's coordinates and updates status to en_route.
    """
    from datetime import datetime
    from shared.state_schema import PatientStatus
    for amb in orchestrator.state.ambulances:
        if amb.is_available or not amb.assigned_patient_id or not amb.route_polyline:
            continue
        patient = next((p for p in orchestrator.state.patient_requests if p.id == amb.assigned_patient_id), None)
        if not patient:
            continue
        
        # Teleport to midpoint (Patient location, index 5 in route polyline)
        mid_idx = min(5, len(amb.route_polyline) - 1)
        amb.current_coordinates = amb.route_polyline[mid_idx]
        patient.status = PatientStatus.EN_ROUTE
        
        start_log_count = len(orchestrator.state.event_log)
        orchestrator._log(f"[Telemetry] {amb.id} ⚡ INSTANT ARRIVAL AT PATIENT. Secured coordinates: {amb.current_coordinates}")
        for i in range(start_log_count, len(orchestrator.state.event_log)):
            orchestrator.state.event_log[i]["incident_id"] = patient.id
        
        return {
            "success": True,
            "message": "Ambulance successfully arrived at patient location. Patient boarded.",
            "current_status": "en_route"
        }
    return {"success": False, "message": "No active emergency dispatch found."}


@app.post("/api/emergency/arrive_hospital")
def arrive_at_hospital():
    """
    Instantly teleports active ambulance to the hospital's coordinates and admits patient.
    """
    from datetime import datetime
    from shared.state_schema import PatientStatus
    for amb in orchestrator.state.ambulances:
        if amb.is_available or not amb.assigned_patient_id or not amb.route_polyline:
            continue
        patient = next((p for p in orchestrator.state.patient_requests if p.id == amb.assigned_patient_id), None)
        if not patient:
            continue
        hospital = next((h for h in orchestrator.state.hospitals if h.id == amb.destination_hospital_id), None)
        if not hospital:
            continue
            
        # Teleport to endpoint (Hospital coordinates)
        end_idx = len(amb.route_polyline) - 1
        amb.current_coordinates = amb.route_polyline[end_idx]
        patient.status = PatientStatus.ADMITTED
        
        start_log_count = len(orchestrator.state.event_log)
        orchestrator._log(f"[Telemetry] {amb.id} ⚡ INSTANT ARRIVAL AT HOSPITAL. Patient admitted to {hospital.name}.")
        for i in range(start_log_count, len(orchestrator.state.event_log)):
            orchestrator.state.event_log[i]["incident_id"] = patient.id
            
        # Reset ambulance back to available
        amb.is_available = True
        amb.assigned_patient_id = None
        amb.destination_hospital_id = None
        amb.route_polyline = []
        
        return {
            "success": True,
            "message": "Ambulance arrived at destination hospital. Patient admitted successfully.",
            "current_status": "admitted"
        }
    return {"success": False, "message": "No active emergency dispatch found."}


@app.post("/api/emergency/reset")
def reset_simulation():
    """
    Resets the backend session memory and database records.
    """
    align_mock_database(write_file=False)
    return {
        "message": "Simulation world state and hospital databases successfully reset."
      }
