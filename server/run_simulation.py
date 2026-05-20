"""
=============================================================
CIRO — Live Simulation Runner
=============================================================
Resets the mock hospital resource registry to default states,
executes various complex test triggers, and prints the full
multi-agent pipeline trace logic showing:
  - Triage reasoning
  - Hospital distance rankings
  - Iterative resource checks + rejections (Fallback logic)
  - Final atomic reservations & dispatch paths
=============================================================
"""

import json
import os
from agents.orchestrator import CIROOrchestrator

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "hospitals.json")

DEFAULT_HOSPITALS = [
  {
    "id": "HOSP-A",
    "name": "Trauma Center Karachi",
    "hospital_type": "Trauma Center",
    "coordinates": [24.8607, 67.0011],
    "available_beds": 5,
    "icu_beds": 0,
    "ventilators": 0,
    "contact_number": "+92-21-35670001",
    "accepts_trauma": True
  },
  {
    "id": "HOSP-B",
    "name": "City General Hospital",
    "hospital_type": "General Hospital",
    "coordinates": [24.8735, 67.0641],
    "available_beds": 12,
    "icu_beds": 3,
    "ventilators": 1,
    "contact_number": "+92-21-35670002",
    "accepts_trauma": False
  },
  {
    "id": "HOSP-C",
    "name": "City Medical Complex",
    "hospital_type": "Specialty Medical Center",
    "coordinates": [24.9056, 67.0822],
    "available_beds": 0,
    "icu_beds": 5,
    "ventilators": 2,
    "contact_number": "+92-21-35670003",
    "accepts_trauma": False
  },
  {
    "id": "HOSP-D",
    "name": "Jinnah Postgraduate Medical Centre",
    "hospital_type": "Teaching Hospital",
    "coordinates": [24.8519, 67.0427],
    "available_beds": 20,
    "icu_beds": 10,
    "ventilators": 5,
    "contact_number": "+92-21-99201300",
    "accepts_trauma": True
  }
]

def reset_registry():
    """Resets the mock hospital JSON database to default resource counts."""
    with open(DATA_PATH, "w") as f:
        json.dump(DEFAULT_HOSPITALS, f, indent=2)
    print("[Simulator] Hospital resource registry successfully reset to pristine states.\n")


def print_log_trace(event_log):
    """Prints a beautiful chronological trace of agent interactions."""
    print("\n" + "="*80)
    print("                      CHRONOLOGICAL AGENT EXECUTION TRACE")
    print("="*80)
    for entry in event_log:
        t = entry["timestamp"]
        agent = entry["agent"].ljust(22)
        msg = entry["message"]
        try:
            print(f"[{t}] | {agent} | {msg}")
        except UnicodeEncodeError:
            safe_msg = msg.encode('ascii', errors='backslashreplace').decode('ascii')
            print(f"[{t}] | {agent} | {safe_msg}")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("="*80)
    print("               CIRO EMERGENCY RESCUE SYSTEM - SIMULATION RUNNER")
    print("="*80)
    
    # Reset database so we start with exact initial counts
    reset_registry()

    # Trigger Scenario 1: Severe accident at Clifton requiring a Ventilator
    # Location Clifton is closest to HOSP-A (Trauma) -> HOSP-D (Jinnah) -> HOSP-B -> HOSP-C
    # HOSP-A has 0 ventilators -> Rejected!
    # Next closest with ventilator: HOSP-D -> Accepted!
    print("Executing Scenario 1: Critical ventilator incident at Clifton...")
    orch_1 = CIROOrchestrator()
    trigger_1 = "Severe head-on accident near Clifton, patient suffocating and not breathing, requires ventilator immediately!"
    result_1 = orch_1.process_trigger(trigger_1)
    print_log_trace(result_1["event_log"])

    # Trigger Scenario 2: Emergency at gulshan, patient needs ICU
    # Location Gulshan is closest to HOSP-C -> HOSP-B -> HOSP-D -> HOSP-A
    # HOSP-C has 0 available beds, but patient requires ICU. HOSP-C has 5 ICU beds -> Accepted!
    print("\nExecuting Scenario 2: Serious ICU incident at Gulshan...")
    orch_2 = CIROOrchestrator()
    trigger_2 = "Cardiac chest pain event at Gulshan, patient unconscious, needs ICU admission"
    result_2 = orch_2.process_trigger(trigger_2)
    print_log_trace(result_2["event_log"])

    # Trigger Scenario 3: Stable fracture at Nazimabad (basic bed)
    # HOSP-C has 0 standard beds -> Rejected!
    # HOSP-B / HOSP-D should take it.
    print("\nExecuting Scenario 3: Basic trauma incident at Nazimabad...")
    orch_3 = CIROOrchestrator()
    trigger_3 = "Road accident at Nazimabad, patient bleeding with minor arm fracture, is stable but needs general bed"
    result_3 = orch_3.process_trigger(trigger_3)
    print_log_trace(result_3["event_log"])
