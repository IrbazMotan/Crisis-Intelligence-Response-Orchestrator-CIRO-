"""
=============================================================
CIRO — Live Telemetry and Movement Simulator Runner
=============================================================
Executes a step-by-step trace of the live ambulance movement
along the DispatchAgent's polyline routes.
=============================================================
"""

import time
from run_simulation import reset_registry
from agents.orchestrator import CIROOrchestrator
from shared.state_schema import PatientStatus

def execute_telemetry_simulation():
    print("=" * 80)
    print("           CIRO EMERGENCY RESCUE SYSTEM - TELEMETRY MOVEMENT SIMULATOR")
    print("=" * 80)
    
    # 1. Reset registry to standard counts
    reset_registry()
    
    # 2. Boot orchestrator
    orch = CIROOrchestrator()
    
    # 3. Trigger emergency event at Clifton requiring ventilator
    trigger = "Severe head-on accident near Clifton, patient suffocating and not breathing, requires ventilator immediately!"
    print(f"\n[Triggering Incident] '{trigger}'")
    pipeline_result = orch.process_trigger(trigger)
    
    if not pipeline_result["success"]:
        print("[Error] Failed to initialize incident pipeline. Aborting.")
        return
        
    patient_id = pipeline_result["patient"]["id"]
    assigned_amb_id = pipeline_result["patient"]["assigned_ambulance"]
    assigned_hosp_id = pipeline_result["patient"]["assigned_hospital"]
    
    print("\n" + "=" * 80)
    print("                       STARTING LIVE TELEMETRY SIMULATION TICKS")
    print("=" * 80)
    print(f"Dispatched Responder : {assigned_amb_id}")
    print(f"Target Patient ID    : {patient_id}")
    print(f"Destination Hospital : {assigned_hosp_id}")
    
    # Find matching ambulance and show initial coordinates
    amb_state = next(a for a in orch.state.ambulances if a.id == assigned_amb_id)
    print(f"Initial Ambulance Location : {amb_state.current_coordinates}")
    print(f"Total Waypoints in Route   : {len(amb_state.route_polyline)}")
    print("-" * 80)

    # 4. Progressively tick the engine until ambulance reaches target
    tick_count = 0
    while not amb_state.is_available or tick_count == 0:
        tick_count += 1
        print(f"\n[Tick #{tick_count:02d}] Executing simulate_tick()...")
        telemetry_logs = orch.simulate_tick()
        
        if not telemetry_logs:
            print("  (No active responders on missions - simulation idle)")
            break
            
        for log in telemetry_logs:
            print(f"  Responder ID       : {log['ambulance_id']}")
            print(f"  Live Coordinates   : {log['current_coordinates']}")
            print(f"  Heading Toward     : {log['target_name']}")
            print(f"  Distance Remaining : {log['distance_remaining']} km")
            print(f"  Step Status        : {log['step_status']}")
            print(f"  Patient Status     : {log['patient_status'].upper()}")
            print("-" * 60)
            
        # Small delay to mimic live movement pacing
        time.sleep(0.5)

    print("\n" + "=" * 80)
    print("                      TELEMETRY SIMULATION COMPLETE")
    print("=" * 80)
    
    # Verify final patient and ambulance statuses
    patient_final = next(p for p in orch.state.patient_requests if p.id == patient_id)
    print(f"Final Patient Status    : {patient_final.status.value.upper()}")
    print(f"Final Ambulance Status  : {'IDLE / AVAILABLE' if amb_state.is_available else 'BUSY'}")
    print(f"Final Coordinates       : {amb_state.current_coordinates}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    execute_telemetry_simulation()
