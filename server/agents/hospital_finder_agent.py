"""
=============================================================
CIRO — HospitalFinderAgent
=============================================================
Agent #2 in the Antigravity pipeline.

Responsibility:
  - Receives patient location + resource needs from TriageAgent
  - Uses get_distance() to rank all hospitals nearest → farthest
  - Iterates sorted list calling check_hospital_resources()
  - FALLBACK LOGIC: Logs rejection reason and skips to next hospital
    if required resource (ICU/ventilator/bed) is unavailable
  - Returns the first hospital that satisfies all requirements
=============================================================
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from shared.state_schema import PatientRequest, Hospital, SystemState
from tools.environment_tools import get_distance, check_hospital_resources
import json, os


class HospitalFinderAgent:
    """
    Antigravity Agent #2 — HospitalFinderAgent

    Input : PatientRequest (from TriageAgent)
    Output: Selected hospital dict + sorted ranking trace
    """

    def __init__(self, state: SystemState):
        self.state = state
        self.name  = "HospitalFinderAgent"

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

    def _load_all_hospitals_in_bounding_box(self, patient_coords, max_radius_km=120) -> List[Dict]:
        """Fetch all nearest hospitals inside the maximum search space in ONE single parallel API call"""
        import concurrent.futures
        import requests
        import random

        lat, lng = patient_coords
        delta = max_radius_km / 111.0
        
        min_lon = lng - delta
        max_lon = lng + delta
        min_lat = lat - delta
        max_lat = lat + delta
        
        search_terms = ["hospital", "clinic", "medical center"]
        h_list = []

        def fetch_term(term):
            url = f"https://nominatim.openstreetmap.org/search?q={term}&format=json&limit=40&viewbox={min_lon},{max_lat},{max_lon},{min_lat}&bounded=1"
            headers = {"User-Agent": "CIRO_Emergency_Orchestrator/1.0"}
            try:
                res = requests.get(url, headers=headers, timeout=2.5)
                if res.status_code == 200:
                    return term, res.json()
            except Exception as e:
                pass
            return term, []

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(fetch_term, search_terms))

        blacklist_terms = [
            "mental", "psychiatric", "psych", "mind", "behavioral", 
            "skin", "dermatology", "dermacare", "cosmetic", 
            "eye", "ophthalmic", "ophthalmology", "vision"
        ]

        for term, elements in results:
            for element in elements:
                h_lat = float(element["lat"])
                h_lon = float(element["lon"])
                display_parts = element["display_name"].split(",")
                h_name = display_parts[0].strip() if display_parts else f"Local {term.title()}"
                
                # Exclude specialized clinics that don't take trauma/emergencies
                h_name_lower = h_name.lower()
                if any(bt in h_name_lower for bt in blacklist_terms):
                    continue
                    
                hid = f"OSM-HOSP-{element['place_id']}"
                if not any(h["id"] == hid for h in h_list):
                    # Check if this hospital is already in the orchestrator's state (loaded from database)
                    existing_state_h = next((h for h in self.state.hospitals if h.id == hid), None)
                    
                    if existing_state_h:
                        avail_beds = existing_state_h.available_beds
                        icu_beds = existing_state_h.icu_beds
                        vents = existing_state_h.ventilators
                        htype = existing_state_h.hospital_type
                    else:
                        htype = "General Hospital"
                        if "clinic" in term:
                            htype = "Local Clinic"
                        elif "medical" in term:
                            htype = "Medical Center"
                            
                        # Check if core registry is completely depleted
                        core_depleted = False
                        if self.state.hospitals:
                            total_beds = sum(h.available_beds for h in self.state.hospitals)
                            total_icu = sum(h.icu_beds for h in self.state.hospitals)
                            total_vents = sum(h.ventilators for h in self.state.hospitals)
                            if total_beds == 0 and total_icu == 0 and total_vents == 0:
                                core_depleted = True

                        # Dynamic random resource seeds
                        if core_depleted:
                            avail_beds = 0
                            icu_beds = 0
                            vents = 0
                        else:
                            avail_beds = random.randint(5, 30)
                            icu_beds = random.randint(1, 10)
                            vents = random.randint(1, 5)
                            if htype == "Local Clinic":
                                avail_beds = random.randint(1, 4)
                                icu_beds = 0
                                vents = 0
                        
                    h_list.append({
                        "id": hid,
                        "name": h_name,
                        "hospital_type": htype,
                        "coordinates": [h_lat, h_lon],
                        "available_beds": avail_beds,
                        "icu_beds": icu_beds,
                        "ventilators": vents
                    })
        return h_list

    def _load_mock_hospitals(self, patient_coords) -> List[Dict]:
        """Generate simulation mock hospitals located near patient coordinates"""
        lat, lng = patient_coords
        
        # Check if core registry is completely depleted
        core_depleted = False
        if self.state.hospitals:
            total_beds = sum(h.available_beds for h in self.state.hospitals)
            total_icu = sum(h.icu_beds for h in self.state.hospitals)
            total_vents = sum(h.ventilators for h in self.state.hospitals)
            if total_beds == 0 and total_icu == 0 and total_vents == 0:
                core_depleted = True

        return [
            {
                "id": "OSM-MOCK-1",
                "name": "Local District Medical Center",
                "hospital_type": "Trauma Center",
                "coordinates": [lat + 0.015, lng + 0.015],
                "available_beds": 0 if core_depleted else 20,
                "icu_beds": 0 if core_depleted else 5,
                "ventilators": 0 if core_depleted else 2
            },
            {
                "id": "OSM-MOCK-2",
                "name": "City General Clinic",
                "hospital_type": "General Hospital",
                "coordinates": [lat - 0.012, lng + 0.020],
                "available_beds": 0 if core_depleted else 15,
                "icu_beds": 0 if core_depleted else 2,
                "ventilators": 0 if core_depleted else 1
            },
            {
                "id": "OSM-MOCK-3",
                "name": "Regional Specialized Hospital",
                "hospital_type": "Specialized Hospital",
                "coordinates": [lat + 0.005, lng - 0.018],
                "available_beds": 0 if core_depleted else 8,
                "icu_beds": 0 if core_depleted else 8,
                "ventilators": 0 if core_depleted else 4
            }
        ]

    def _sort_by_distance(self, patient_coords, hospitals: List[Dict]) -> List[Dict]:
        """Sort hospitals by Live OSRM road distance and ETA from patient location, prioritizing actual hospitals over clinics."""
        import math
        # 1. Fast mathematical sort first
        p_lat, p_lon = patient_coords
        for h in hospitals:
            h_lat, h_lon = h["coordinates"]
            # Haversine distance
            R = 6371.0
            dlat = math.radians(h_lat - p_lat)
            dlon = math.radians(h_lon - p_lon)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(p_lat)) * math.cos(math.radians(h_lat)) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            h["_hav_dist"] = R * c
            h["type_priority"] = 1 if h.get("hospital_type") == "Local Clinic" else 0

        # Sort candidate pool by type_priority first, then raw haversine distance
        hospitals_sorted_hav = sorted(hospitals, key=lambda h: (h["type_priority"], h["_hav_dist"]))
        
        # 2. Only calculate OSRM for the top 5 candidates
        top_n = hospitals_sorted_hav[:5]
        for h in top_n:
            result = get_distance(patient_coords, tuple(h["coordinates"]))
            h["_distance_km"]  = result["distance_km"]
            h["_eta_minutes"]  = result["eta_minutes"]
            h["_route_source"] = result.get("source", "HAVERSINE")
            
        # For the remaining candidates, fill with haversine fallback to avoid calling OSRM
        for h in hospitals_sorted_hav[5:]:
            h["_distance_km"]  = round(h["_hav_dist"], 2)
            h["_eta_minutes"]  = max(1, int(h["_hav_dist"] * 1.5))
            h["_route_source"] = "HAVERSINE_FAST_FALLBACK"

        return sorted(hospitals_sorted_hav, key=lambda h: (h["type_priority"], h["_eta_minutes"], h["_distance_km"]))

    def _check_fit(self, h_meta: Dict, resources: Dict, patient: PatientRequest) -> tuple:
        """
        Checks if a hospital satisfies patient resource needs AND road/management conditions.

        Returns:
            (is_fit: bool, rejection_reason: str)
        """
        self._log(f"Contacting Hospital Management at {resources['name']} for admission clearance...")
        
        # 1. Road Blockage Check (Based on real map ETA vs Distance)
        # If the map says the ETA is over 45 minutes for a city trip, assume traffic/roadblock
        if h_meta["_eta_minutes"] > 45:
            return False, f"CRITICAL REJECTION: Live Map Routing shows road is blocked or heavily congested (ETA {h_meta['_eta_minutes']} min). Skipping to next nearer hospital."

        # 2. Management / Bed Check
        if patient.requires_ventilator and resources["ventilators"] < 1:
            return False, f"MANAGEMENT REJECTION: Hospital [{resources['name']}] management cannot admit. Lacks specialized ICU ventilators. Re-routing agent to next nearest map node..."

        if patient.requires_icu and resources["icu_beds"] < 1:
            return False, f"MANAGEMENT REJECTION: Hospital [{resources['name']}] management cannot admit. Lacks available ICU beds. Re-routing agent to next nearest map node..."

        if resources["available_beds"] < 1 and not patient.requires_icu:
            return False, f"MANAGEMENT REJECTION: {resources['name']} management refuses admission (0 general beds). Re-routing to next nearest map node..."

        # If ICU-only patient, they go to ICU, standard beds not needed
        if patient.requires_icu and resources["icu_beds"] >= 1:
            return True, "ACCEPTED - ICU bed available"

        if resources["available_beds"] >= 1:
            return True, "ACCEPTED - Standard bed available"

        return False, f"REJECTED - {resources['name']} has no suitable resource"

    def run(self, patient: PatientRequest) -> Optional[Dict]:
        """
        Finds the best available hospital for the patient with ultra-low latency.
        Fetches all candidates in ONE single map call, then evaluates progressive ring fitness in-memory.
        """
        self._log("=" * 55)
        self._log(f"HOSPITAL SEARCH INITIATED for [{patient.id}]")
        self._log(f"Patient Location : {patient.location}")
        self._log(f"Needs ICU        : {patient.requires_icu}")
        self._log(f"Needs Ventilator : {patient.requires_ventilator}")
        self._log("=" * 55)

        self._log("Fetching all regional candidate nodes in a single parallel API query...")
        all_candidates = self._load_all_hospitals_in_bounding_box(patient.location, max_radius_km=120)
        
        # Merge the core registry hospitals stored in self.state.hospitals into all_candidates
        core_candidates = []
        for h in self.state.hospitals:
            core_candidates.append({
                "id": h.id,
                "name": h.name,
                "hospital_type": h.hospital_type,
                "coordinates": list(h.coordinates),
                "available_beds": h.available_beds,
                "icu_beds": h.icu_beds,
                "ventilators": h.ventilators
            })
        for h in core_candidates:
            if not any(cand["id"] == h["id"] for cand in all_candidates):
                all_candidates.insert(0, h) # Prioritize core candidates
                
        self._log(f"Pre-fetched {len(all_candidates)} candidates within 120km (including {len(core_candidates)} core registry hospitals).")

        # Progressive Ring boundaries
        search_radii_km = [5, 15, 30, 60, 80, 100, 120]
        evaluated_hospital_ids = set()

        for radius in search_radii_km:
            self._log(f"=== EVALUATING LOCAL RING: {radius} km radius ===")
            
            # Filter candidates inside this radius locally
            ring_candidates = []
            for h in all_candidates:
                if h["id"] in evaluated_hospital_ids:
                    continue
                # Calculate fast direct distance to check if it fits in this ring boundary
                h_lat, h_lon = h["coordinates"]
                p_lat, p_lon = patient.location
                # Basic quick haversine distance for ring grouping
                import math
                R = 6371.0
                dlat = math.radians(h_lat - p_lat)
                dlon = math.radians(h_lon - p_lon)
                a = math.sin(dlat/2)**2 + math.cos(math.radians(p_lat)) * math.cos(math.radians(h_lat)) * math.sin(dlon/2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                dist = R * c
                
                if dist <= radius:
                    ring_candidates.append(h)

            if not ring_candidates:
                self._log(f"No new medical facilities located inside the {radius} km ring.")
                continue

            self._log(f"Discovered {len(ring_candidates)} new facilities inside the {radius} km ring. Calculating OSRM routes...")
            
            # Sort the local candidates inside this ring by road ETA and priority
            sorted_hospitals = self._sort_by_distance(patient.location, ring_candidates)
            
            self._log("Distance and road ETA ranking for this search ring:")
            for rank, h in enumerate(sorted_hospitals, 1):
                self._log(f"  #{rank} {h['name']} - {h['_distance_km']} km | ETA: {h['_eta_minutes']} min")

            self._log("Checking resource fitness sequentially (nearest/fastest first)...")
            for attempt, h in enumerate(sorted_hospitals, 1):
                evaluated_hospital_ids.add(h["id"])
                self._log(f"--- Ring {radius}km Check #{attempt}: {h['name']} ({h['id']}) ---")
                
                if h["id"].startswith("OSM-"):
                    resources = {
                        "hospital_id": h["id"],
                        "name": h["name"],
                        "hospital_type": h["hospital_type"],
                        "available_beds": h["available_beds"],
                        "icu_beds": h["icu_beds"],
                        "ventilators": h["ventilators"],
                        "accepts_trauma": True,
                        "coordinates": h["coordinates"],
                        "found": True
                    }
                else:
                    resources = check_hospital_resources(h["id"])
                    resources["hospital_type"] = "General Hospital"

                self._log(f"  TOOL CALL -> verify_hospital_inventory('{h['id']}')")
                self._log(f"  Response  -> Beds: {resources['available_beds']} | "
                          f"ICU: {resources['icu_beds']} | "
                          f"Ventilators: {resources['ventilators']}")

                is_fit, reason = self._check_fit(h, resources, patient)
                self._log(f"  Fit Check -> {reason}")

                if is_fit:
                    h["_resources"] = resources
                    self._log(f"Hospital SELECTED: {h['name']} | Proximity: {h['_distance_km']} km | ETA: {h['_eta_minutes']} min")
                    return h

            self._log(f"All facilities in the {radius} km ring were rejected or full. Expanding to next ring...")

        # Fallback to simulation mock generation strictly near the patient if map returns nothing
        self._log("WARNING: No suitable live map hospital found in any radius. Falling back to dynamic mock generation near patient coordinates...")
        mock_hospitals = self._load_mock_hospitals(patient.location)
        sorted_mocks = self._sort_by_distance(patient.location, mock_hospitals)
        
        for h in sorted_mocks:
            resources = {
                "hospital_id": h["id"],
                "name": h["name"],
                "hospital_type": h["hospital_type"],
                "available_beds": h["available_beds"],
                "icu_beds": h["icu_beds"],
                "ventilators": h["ventilators"],
                "accepts_trauma": True,
                "coordinates": h["coordinates"],
                "found": True
            }
            is_fit, reason = self._check_fit(h, resources, patient)
            if is_fit:
                h["_resources"] = resources
                self._log(f"[FALLBACK SELECTED] {h['name']} | Proximity: {h['_distance_km']} km | ETA: {h['_eta_minutes']} min")
                return h

        self._log("CRITICAL: Absolutely no hospital (live or mock) could satisfy patient emergency resources!")
        return None
