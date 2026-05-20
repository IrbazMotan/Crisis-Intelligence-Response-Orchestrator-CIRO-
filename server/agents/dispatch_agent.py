"""
=============================================================
CIRO — DispatchAgent
=============================================================
Agent #3 in the Antigravity pipeline.

Responsibility:
  - Receives the assigned patient request and the selected hospital.
  - Reserves the appropriate resource at the hospital using 'reserve_bed'.
  - Identifies an available ambulance (or spawns one close by).
  - Generates a simulated polyline path: Ambulance -> Patient -> Hospital.
  - Updates SystemState (Patient and Ambulance states) accordingly.
=============================================================
"""

from typing import Dict, Any, Tuple, List
from datetime import datetime
from shared.state_schema import (
    PatientRequest, PatientStatus, AmbulanceState, SystemState, ResourceType
)
from tools.environment_tools import reserve_bed, get_distance


class DispatchAgent:
    """
    Antigravity Agent #3 — DispatchAgent

    Input : PatientRequest, Selected Hospital dict
    Output: Updated SystemState with ambulance route and reserved beds
    """

    def __init__(self, state: SystemState):
        self.state = state
        self.name  = "DispatchAgent"

    def _log(self, message: str):
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "agent":     self.name,
            "message":   message
        }
        self.state.event_log.append(entry)
        try:
            print(f"  [{entry['timestamp']}] [{self.name}] {message}")
        except UnicodeEncodeError:
            safe_message = message.encode('ascii', errors='backslashreplace').decode('ascii')
            print(f"  [{entry['timestamp']}] [{self.name}] {safe_message}")

    def _find_available_ambulance(self, patient_coords: Tuple[float, float]) -> AmbulanceState:
        """Finds the closest available ambulance, or spawns one if none exist."""
        available_ambs = [amb for amb in self.state.ambulances if amb.is_available]
        
        if not available_ambs:
            # Spawn a default mock ambulance slightly offset from the patient to simulate distance
            amb_id = f"AMB-{len(self.state.ambulances) + 1:02d}"
            spawn_coords = (patient_coords[0] + 0.02, patient_coords[1] - 0.02)
            self._log(f"No free ambulances in queue. Spawning a new emergency responder: {amb_id} at {spawn_coords}")
            new_amb = AmbulanceState(
                id=amb_id,
                current_coordinates=spawn_coords,
                is_available=True
            )
            self.state.ambulances.append(new_amb)
            return new_amb

        # Find closest available ambulance
        closest_amb = None
        min_dist = float('inf')
        for amb in available_ambs:
            dist = get_distance(amb.current_coordinates, patient_coords)["distance_km"]
            if dist < min_dist:
                min_dist = dist
                closest_amb = amb

        self._log(f"Located closest available responder: {closest_amb.id} ({min_dist} km away)")
        return closest_amb

    def _generate_simulated_polyline(self, start: Tuple[float, float], mid: Tuple[float, float], end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Generates REAL road GPS waypoints between three nodes using LIVE OSRM API."""
        import requests
        waypoints = []
        
        self._log("Fetching LIVE OSRM coordinates for Ambulance -> Patient leg...")
        try:
            url1 = f"https://router.project-osrm.org/route/v1/driving/{start[1]},{start[0]};{mid[1]},{mid[0]}?overview=full&geometries=geojson"
            res1 = requests.get(url1, timeout=4)
            if res1.status_code == 200:
                coords1 = res1.json()["routes"][0]["geometry"]["coordinates"]
                for c in coords1:
                    waypoints.append((c[1], c[0]))
        except Exception as e:
            self._log(f"[WARNING] OSRM Segment 1 failed ({e}). Using linear fallback.")
            # Linear fallback
            for i in range(6):
                t = i / 5
                waypoints.append((start[0] + (mid[0] - start[0]) * t, start[1] + (mid[1] - start[1]) * t))
                
        self._log("Fetching LIVE OSRM coordinates for Patient -> Hospital leg...")
        try:
            url2 = f"https://router.project-osrm.org/route/v1/driving/{mid[1]},{mid[0]};{end[1]},{end[0]}?overview=full&geometries=geojson"
            res2 = requests.get(url2, timeout=4)
            if res2.status_code == 200:
                coords2 = res2.json()["routes"][0]["geometry"]["coordinates"]
                for c in coords2[1:]: # Skip first point to avoid duplicate middle point
                    waypoints.append((c[1], c[0]))
        except Exception as e:
            self._log(f"[WARNING] OSRM Segment 2 failed ({e}). Using linear fallback.")
            for i in range(1, 6):
                t = i / 5
                waypoints.append((mid[0] + (end[0] - mid[0]) * t, mid[1] + (end[1] - mid[1]) * t))

        return waypoints

    def run(self, patient: PatientRequest, hospital_dict: Dict[str, Any]) -> bool:
        """
        Executes the reservation, ambulance dispatch, and route mapping pipeline.
        """
        self._log("=" * 55)
        self._log(f"DISPATCH ORCHESTRATION INITIATED FOR [{patient.id}]")
        self._log(f"Target Hospital  : {hospital_dict['name']} ({hospital_dict['id']})")
        self._log("=" * 55)

        # 1. Determine resource type to reserve
        resource_to_reserve = "bed"
        if patient.requires_ventilator:
            resource_to_reserve = "ventilator"
        elif patient.requires_icu:
            resource_to_reserve = "icu"

        self._log(f"Step 1 - Reserving resource type: '{resource_to_reserve.upper()}' at hospital...")
        
        # TOOL CALL: reserve_bed
        res = reserve_bed(hospital_dict["id"], resource_to_reserve)
        self._log(f"  TOOL CALL -> reserve_bed('{hospital_dict['id']}', '{resource_to_reserve}')")
        self._log(f"  Response  -> Success: {res.get('success')} | Message: {res.get('message')}")

        if not res.get("success"):
            self._log("Critical Reservation Failure! Aborting dispatch workflow.")
            return False

        # Update the in-memory shared state for self.state.hospitals
        h_state = next((h for h in self.state.hospitals if h.id == hospital_dict["id"]), None)
        if h_state:
            if resource_to_reserve == "ventilator" and h_state.ventilators > 0:
                h_state.ventilators -= 1
            elif resource_to_reserve == "icu" and h_state.icu_beds > 0:
                h_state.icu_beds -= 1
            elif resource_to_reserve == "bed" and h_state.available_beds > 0:
                h_state.available_beds -= 1
            self._log(f"In-memory resource decremented for {h_state.id} ({resource_to_reserve.upper()}). Remaining in memory: Beds={h_state.available_beds}, ICU={h_state.icu_beds}, Vents={h_state.ventilators}")
        else:
            # Dynamic map hospital selected. Register it to self.state.hospitals to track its resources
            from shared.state_schema import Hospital
            new_h = Hospital(
                id=hospital_dict["id"],
                name=hospital_dict["name"],
                hospital_type=hospital_dict.get("hospital_type", "General Hospital"),
                coordinates=tuple(hospital_dict["coordinates"]),
                available_beds=hospital_dict.get("available_beds", 10),
                icu_beds=hospital_dict.get("icu_beds", 2),
                ventilators=hospital_dict.get("ventilators", 1),
                contact_number=hospital_dict.get("contact_number", "+92-00-0000000"),
                accepts_trauma=hospital_dict.get("accepts_trauma", True)
            )
            if resource_to_reserve == "ventilator" and new_h.ventilators > 0:
                new_h.ventilators -= 1
            elif resource_to_reserve == "icu" and new_h.icu_beds > 0:
                new_h.icu_beds -= 1
            elif resource_to_reserve == "bed" and new_h.available_beds > 0:
                new_h.available_beds -= 1
            self.state.hospitals.append(new_h)
            self._log(f"Registered dynamic map hospital to SystemState: {new_h.id} ({resource_to_reserve.upper()} reserved).")

        # 2. Dispatch Ambulance
        self._log("Step 2 - Assigning emergency vehicle responder...")
        ambulance = self._find_available_ambulance(patient.location)

        # 3. Generate route path
        self._log("Step 3 - Mapping optimal telemetry routes...")
        hosp_coords = tuple(hospital_dict["coordinates"])
        route_polyline = self._generate_simulated_polyline(
            ambulance.current_coordinates,
            patient.location,
            hosp_coords
        )
        self._log(f"  Generated 2-segment navigation path ({len(route_polyline)} dynamic coordinate points)")

        # 4. Update state variables atomically
        self._log("Step 4 - Finalizing System State Schema modifications...")
        
        # Update Patient
        patient.status = PatientStatus.DISPATCHED
        patient.assigned_ambulance = ambulance.id
        patient.assigned_hospital = hospital_dict["id"]

        # Update Ambulance
        ambulance.is_available = False
        ambulance.assigned_patient_id = patient.id
        ambulance.destination_hospital_id = hospital_dict["id"]
        ambulance.route_polyline = route_polyline

        self._log(f"DISPATCH COMPLETE!")
        self._log(f"  Patient Status       : DISPATCHED")
        self._log(f"  Ambulance dispatched : {ambulance.id}")
        self._log(f"  Assigned Hospital    : {hospital_dict['name']}")
        return True
