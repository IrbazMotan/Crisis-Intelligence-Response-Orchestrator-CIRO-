"""
=============================================================
CIRO — Multi-Agent Orchestrator
=============================================================
Coordinates the lifecycle of an emergency event trigger.

Loads initial system states (hospitals, responders), runs
triage, initiates resource search with fallback checks,
and coordinates ambulance dispatch.
=============================================================
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime

from shared.state_schema import (
    SystemState, PatientRequest, AmbulanceState, Hospital, ConditionSeverity, PatientStatus
)
from agents.triage_agent import TriageAgent
from agents.hospital_finder_agent import HospitalFinderAgent
from agents.dispatch_agent import DispatchAgent
from tools.environment_tools import get_distance


class CIROOrchestrator:
    """
    Main orchestration brain for CIRO Platform.
    Ties the TriageAgent, HospitalFinderAgent, and DispatchAgent together.
    """

    def __init__(self):
        # 1. Initialize empty SystemState
        self.state = SystemState()
        self._load_initial_state()

        # 2. Instantiate Agents
        self.triage_agent = TriageAgent(self.state)
        self.finder_agent = HospitalFinderAgent(self.state)
        self.dispatch_agent = DispatchAgent(self.state)

    def _log(self, message: str):
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "agent":     "Orchestrator",
            "message":   message
        }
        self.state.event_log.append(entry)
        try:
            print(f"[{entry['timestamp']}] [Orchestrator] {message}")
        except UnicodeEncodeError:
            safe_message = message.encode('ascii', errors='backslashreplace').decode('ascii')
            print(f"[{entry['timestamp']}] [Orchestrator] {safe_message}")

    def _load_initial_state(self):
        """Loads default hospitals from json registry and spawns initial ambulances."""
        self._log("Initializing World State...")
        
        # Load hospitals
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "hospitals.json")
        try:
            with open(data_path, "r") as f:
                hosp_list = json.load(f)
                
            for h in hosp_list:
                hosp_obj = Hospital(
                    id=h["id"],
                    name=h["name"],
                    hospital_type=h["hospital_type"],
                    coordinates=tuple(h["coordinates"]),
                    available_beds=h["available_beds"],
                    icu_beds=h["icu_beds"],
                    ventilators=h["ventilators"],
                    contact_number=h["contact_number"],
                    accepts_trauma=h.get("accepts_trauma", False)
                )
                self.state.hospitals.append(hosp_obj)
            self._log(f"Successfully loaded {len(self.state.hospitals)} hospitals into memory.")
        except Exception as e:
            self._log(f"Error loading hospitals registry: {e}")

        # Spawn some active/available ambulances at strategic coordinates
        initial_ambs = [
            AmbulanceState(id="AMB-01", current_coordinates=(24.8201, 67.0315), is_available=True),
            AmbulanceState(id="AMB-02", current_coordinates=(24.9120, 67.0780), is_available=True),
            AmbulanceState(id="AMB-03", current_coordinates=(24.8700, 67.0500), is_available=False) # occupied
        ]
        self.state.ambulances.extend(initial_ambs)
        self._log(f"Initialized {len(self.state.ambulances)} ambulance dispatch responders ({len([a for a in initial_ambs if a.is_available])} available).")

    def process_trigger(self, trigger_text: str, live_coords: tuple = None) -> Dict[str, Any]:
        """
        Ingests a raw emergency call, pipelines it through the agents,
        modifies shared state, and returns execution summary logs.
        """
        self._log("=" * 80)
        self._log(f"STARTING EMERGENCY PIPELINE PIPELINE RUN")
        self._log("=" * 80)

        # 1. Triage the event
        patient_req = self.triage_agent.run(trigger_text, live_coords=live_coords)

        # Intercept weather-based security fraud rejections
        if patient_req.confidence == 0.0:
            self._log("[FRAUD REJECTION] PIPELINE REJECTED: Security verification failed. Sensor anomaly or coordinates mismatch detected.")
            # Add a trace event log entry specifically for the dashboard
            self.state.event_log.append({
                "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                "agent": "Orchestrator",
                "message": f"CRITICAL [FRAUD REJECTION] REQ-{patient_req.id}: Aborted. Details: {patient_req.explanation}"
            })
            self._log("=" * 80)
            self._log("PIPELINE RUN COMPLETE - Status: REJECTED (FRAUD)")
            self._log("=" * 80)
            return {
                "success": False,
                "patient": {
                    "id": patient_req.id,
                    "location": patient_req.location,
                    "severity": patient_req.severity.value,
                    "requires_icu": patient_req.requires_icu,
                    "requires_ventilator": patient_req.requires_ventilator,
                    "status": "rejected",
                    "explanation": patient_req.explanation,
                    "assigned_ambulance": None,
                    "assigned_hospital": None
                },
                "event_log": self.state.event_log
            }

        # 2. Discover nearest available hospital satisfying the resource parameters
        assigned_hosp = self.finder_agent.run(patient_req)

        success = False
        if assigned_hosp:
            # 3. Dynamic registration of dynamic/OSM hospitals in the state registry
            h_id = assigned_hosp["id"]
            existing = next((h for h in self.state.hospitals if h.id == h_id), None)
            if not existing:
                from shared.state_schema import Hospital
                new_h = Hospital(
                    id=h_id,
                    name=assigned_hosp["name"],
                    hospital_type=assigned_hosp.get("hospital_type", "General Hospital"),
                    coordinates=tuple(assigned_hosp["coordinates"]),
                    available_beds=assigned_hosp.get("available_beds", 15),
                    icu_beds=assigned_hosp.get("icu_beds", 5),
                    ventilators=assigned_hosp.get("ventilators", 2),
                    contact_number=assigned_hosp.get("contact_number", "+92-111-111-111"),
                    accepts_trauma=assigned_hosp.get("accepts_trauma", True)
                )
                self.state.hospitals.append(new_h)
                
                # Persist to hospitals.json
                db_path = os.path.join(os.path.dirname(__file__), "..", "data", "hospitals.json")
                if os.path.exists(db_path):
                    try:
                        with open(db_path, "r") as f:
                            hosp_list = json.load(f)
                        if not any(h["id"] == h_id for h in hosp_list):
                            hosp_list.append({
                                "id": h_id,
                                "name": new_h.name,
                                "hospital_type": new_h.hospital_type,
                                "coordinates": list(new_h.coordinates),
                                "available_beds": new_h.available_beds,
                                "icu_beds": new_h.icu_beds,
                                "ventilators": new_h.ventilators,
                                "contact_number": new_h.contact_number,
                                "accepts_trauma": new_h.accepts_trauma
                            })
                            with open(db_path, "w") as f:
                                json.dump(hosp_list, f, indent=2)
                    except Exception as e:
                        self._log(f"[WARNING] Failed to persist new hospital to JSON: {e}")
                        
            # 4. Reserve resource and dispatch responder
            success = self.dispatch_agent.run(patient_req, assigned_hosp)
        else:
            self._log("[FAILED] PIPELINE ABORTED: No suitable hospitals found to route patients.")

        self._log("=" * 80)
        self._log(f"PIPELINE RUN COMPLETE - Status: {'SUCCESS' if success else 'FAILED'}")
        self._log("=" * 80)

        # Build output structure
        return {
            "success": success,
            "patient": {
                "id": patient_req.id,
                "location": patient_req.location,
                "severity": patient_req.severity.value,
                "requires_icu": patient_req.requires_icu,
                "requires_ventilator": patient_req.requires_ventilator,
                "status": patient_req.status.value,
                "explanation": patient_req.explanation,
                "assigned_ambulance": patient_req.assigned_ambulance,
                "assigned_hospital": patient_req.assigned_hospital
            },
            "event_log": self.state.event_log
        }

    def simulate_tick(self) -> List[Dict[str, Any]]:
        """
        Executes one simulation tick for all active, dispatched ambulances.
        Moves them progressively along their route polylines, updates patient/ambulance
        status, and returns/logs state-change information for frontend telemetry.
        """
        logs = []
        
        for amb in self.state.ambulances:
            if amb.is_available or not amb.assigned_patient_id or not amb.route_polyline:
                continue
                
            # 1. Fetch associated patient request
            patient = next((p for p in self.state.patient_requests if p.id == amb.assigned_patient_id), None)
            if not patient:
                continue
                
            # 2. Fetch associated hospital
            hospital = next((h for h in self.state.hospitals if h.id == amb.destination_hospital_id), None)
            if not hospital:
                continue

            # 3. Find current position index in route_polyline
            route = amb.route_polyline
            current_coords = amb.current_coordinates
            
            # Look up closest match in the polyline waypoints
            current_idx = 0
            min_dist = float('inf')
            for idx, pt in enumerate(route):
                dist_res = get_distance(current_coords, pt)
                dist = dist_res["distance_km"]
                if dist < min_dist:
                    min_dist = dist
                    current_idx = idx

            # 4. Advance index by 1
            next_idx = current_idx + 1
            if next_idx >= len(route):
                # Already at the destination (hospital)
                amb.is_available = True
                amb.assigned_patient_id = None
                amb.destination_hospital_id = None
                amb.route_polyline = []
                patient.status = PatientStatus.ADMITTED
                continue
                
            new_coords = route[next_idx]
            amb.current_coordinates = new_coords
            
            # 5. Determine Phase & Targets
            # Midpoint is exactly patient location (route[5])
            mid_idx = 5
            
            if next_idx < mid_idx:
                # Phase 1: Moving to Patient
                target_coords = patient.location
                target_name = "Patient Location"
                step_status = "Phase 1: Responder dispatched. Moving to Patient Location."
                patient.status = PatientStatus.DISPATCHED
            elif next_idx == mid_idx:
                # Phase 1 complete: Arrived at Patient
                target_coords = patient.location
                target_name = "Patient Location"
                step_status = "Phase 1 Complete: Arrived at patient location. Patient boarded. Status: EN_ROUTE."
                patient.status = PatientStatus.EN_ROUTE
            elif next_idx < len(route) - 1:
                # Phase 2: Moving to Hospital
                target_coords = hospital.coordinates
                target_name = hospital.name
                step_status = f"Phase 2: En Route. Transporting patient to {hospital.name}."
                patient.status = PatientStatus.EN_ROUTE
            else:
                # Phase 2 complete: Arrived at Hospital
                target_coords = hospital.coordinates
                target_name = hospital.name
                step_status = f"Phase 2 Complete: Arrived at {hospital.name}. Patient successfully admitted. Responder released."
                patient.status = PatientStatus.ADMITTED
                
                # Reset ambulance back to available
                amb.is_available = True
                amb.assigned_patient_id = None
                amb.destination_hospital_id = None
                amb.route_polyline = []

            # 6. Calculate remaining distance to target
            dist_res = get_distance(new_coords, target_coords)
            distance_remaining = dist_res["distance_km"]
            
            # Log event trace in the state
            log_msg = f"[Telemetry] {amb.id} -> Coordinates: {new_coords} | Target: {target_name} | Distance Remaining: {distance_remaining} km | Status: {step_status}"
            self._log(log_msg)
            
            logs.append({
                "ambulance_id":        amb.id,
                "current_coordinates": new_coords,
                "target_name":         target_name,
                "distance_remaining":  distance_remaining,
                "step_status":         step_status,
                "patient_status":      patient.status.value
            })
            
        return logs
