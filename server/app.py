"""
=============================================================
CIRO — Mobile API Integration Wrapper (FastAPI)
=============================================================
Exposes the Google Antigravity emergency rescue multi-agent
workflow and real-time movement telemetry to client apps.
=============================================================
"""

import os
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.state_schema import PatientStatus
from agents.orchestrator import CIROOrchestrator

# Initialize FastAPI App
app = FastAPI(
    title="CIRO Emergency Rescue System API",
    description="Google Antigravity-compatible API integration wrapper for mobile rescue clients",
    version="1.0.0"
)

# Enable CORS for mobile app client access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Orchestrator Singleton keeping active SystemState in-memory
orchestrator = CIROOrchestrator()


# ─────────────────────────────────────────────
# PYDANTIC SCHEMAS
# ─────────────────────────────────────────────

class TriggerRequest(BaseModel):
    text: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/")
def get_root():
    return {
        "status": "healthy",
        "system": "CIRO Emergency Rescue Backend",
        "active_incidents": len(orchestrator.state.patient_requests),
        "total_responders": len(orchestrator.state.ambulances)
    }


@app.post("/api/emergency/trigger", status_code=status.HTTP_201_CREATED)
def trigger_emergency(payload: TriggerRequest):
    """
    Ingests an unstructured emergency call or GPS pin from a user device,
    executes the triage and dispatch pipeline, and returns the incident acknowledgment.
    """
    # 1. Format the trigger text if coordinates are passed directly
    trigger_text = payload.text
    live_coords = None
    if payload.latitude is not None and payload.longitude is not None:
        trigger_text = f"{payload.text} at coordinates ({payload.latitude}, {payload.longitude})"
        live_coords = (payload.latitude, payload.longitude)

    # 2. Execute the multi-agent pipeline run
    result = orchestrator.process_trigger(trigger_text, live_coords=live_coords)
    patient_data = result["patient"]
    incident_id = patient_data["id"]

    # 3. Override patient request coordinates if pin was explicitly sent
    if live_coords:
        patient_req = next((p for p in orchestrator.state.patient_requests if p.id == incident_id), None)
        if patient_req:
            patient_req.location = live_coords
            # Re-fetch from state for final payload
            patient_data["location"] = patient_req.location

    # 4. Handle fully-occupied/no-hospital warning logic
    if not result["success"]:
        # All mock hospitals are fully occupied or rejected during fallback checks
        warning_msg = (
            "CRITICAL: No available hospital beds found across all regional trauma registries. "
            "Patient remains in PENDING triage queue."
        )
        return {
            "success": False,
            "incident_id": incident_id,
            "status": "warning",
            "message": "All mock hospitals are fully occupied. Emergency is registered but pending resource assignment.",
            "warning": warning_msg,
            "patient_status": PatientStatus.PENDING.value,
            "patient_details": patient_data
        }

    # 5. Pipeline success: Dispatch finalized
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
    Returns the real-time telemetry state of the crisis, including trace logs,
    patient status, responder location, and hospital resource allocations.
    """
    # 1. Fetch patient
    patient = next((p for p in orchestrator.state.patient_requests if p.id == incident_id), None)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found."
        )

    # 2. Filter system event logs for this specific incident
    incident_logs = [
        log for log in orchestrator.state.event_log 
        if incident_id in log["message"] or incident_id in log.get("agent", "")
    ]

    # 3. Retrieve assigned ambulance coordinates
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
                "coordinates": hosp.coordinates,
                "available_beds": hosp.available_beds,
                "icu_beds": hosp.icu_beds,
                "ventilators": hosp.ventilators,
                "contact_number": hosp.contact_number
            }

    # 5. Handle Fully Occupied warning logic
    if not patient.assigned_hospital:
        warning_msg = (
            "CRITICAL: No available hospital beds found across all regional trauma registries. "
            "Patient remains in PENDING triage queue."
        )
        return {
            "success": False,
            "incident_id": incident_id,
            "status": "warning",
            "message": "No hospital resource assigned. Regional beds exhausted.",
            "warning": warning_msg,
            "patient_status": patient.status.value,
            "trace_logs": incident_logs,
            "ambulance_telemetry": None,
            "hospital_telemetry": None
        }

    # 6. Success payload
    return {
        "success": True,
        "incident_id": incident_id,
        "status": "active",
        "patient_status": patient.status.value,
        "trace_logs": incident_logs,
        "ambulance_telemetry": ambulance_telemetry,
        "hospital_telemetry": hospital_telemetry
    }


@app.post("/api/emergency/tick")
def trigger_telemetry_tick():
    """
    Voluntary endpoint to trigger a simulation movement step for all active responders.
    Returns the dynamic GPS updates to synchronize mobile map frontends.
    """
    telemetry = orchestrator.simulate_tick()
    return {
        "tick_status": "executed",
        "active_responders": len(telemetry),
        "telemetry": telemetry
    }


@app.post("/api/emergency/reset")
def reset_simulation():
    """
    Resets the simulation memory to test fresh incidents.
    """
    global orchestrator
    orchestrator = CIROOrchestrator()
    return {
        "message": "Simulation world state and hospital registries successfully reset."
    }
