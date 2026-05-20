import os
import sys

# Add server directory to path
sys.path.append(r"c:\Users\PMLS\OneDrive - Punjab Group of Colleges\Desktop\hathakon\ciro_platform\server")

from shared.state_schema import SystemState
from agents.triage_agent import TriageAgent
from agents.crisis_intelligence_agent import CrisisIntelligenceAgent

# Initialize System State
state = SystemState()

print("Initializing TriageAgent...")
triage = TriageAgent(state)

print("Initializing CrisisIntelligenceAgent...")
ci = CrisisIntelligenceAgent(state)

print("\n--- Test 1: TriageAgent geocoding with Baloch Colony Bridge in Roman-Urdu ---")
req1 = triage.run("balouch ka pull pe aag lag gayi hai")
print(f"Extracted Location Coordinates: {req1.location}")
print(f"Severity: {req1.severity}")

print("\n--- Test 2: TriageAgent geocoding with Clifton 5 ---")
req2 = triage.run("clifton 5 ke qareeb severe accident hoa hai")
print(f"Extracted Location Coordinates: {req2.location}")
print(f"Severity: {req2.severity}")

print("\n--- Test 3: CrisisIntelligenceAgent with multi-signal input ---")
signals = [
    "clifton 5 ami to pani bahra hau hai",
    "stadium road pe boht pani hai"
]
result = ci.analyze_signals(signals, city="Karachi")
print("Analysis Results:")
for s in result.get("signals", []):
    print(f"Signal: {s['post']}")
    print(f"  Geocoded Location: {s['location']}")
    print(f"  Coordinates: {s['coordinates']}")
    print(f"  Valid: {s['is_valid']}")
    print(f"  Reason: {s['reason']}")
