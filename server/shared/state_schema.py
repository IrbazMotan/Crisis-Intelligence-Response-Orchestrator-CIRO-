"""
=============================================================
CIRO — Emergency Rescue System
Shared State Schema (Google Antigravity Compatible)
=============================================================

All agents in the multi-agent pipeline share this state.
Each field is typed using Python dataclasses + Enums for
strict validation and IDE autocomplete support.
=============================================================
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class PatientStatus(str, Enum):
    """Lifecycle of a patient request through the system."""
    PENDING     = "pending"       # Request received, not yet acted on
    DISPATCHED  = "dispatched"    # Ambulance assigned, not yet moving
    EN_ROUTE    = "en_route"      # Ambulance moving toward patient/hospital
    ADMITTED    = "admitted"      # Patient successfully admitted to hospital
    REJECTED    = "rejected"      # Request rejected due to fraud validation


class ResourceType(str, Enum):
    """Types of hospital resources that can be reserved."""
    BED         = "bed"
    ICU         = "icu"
    VENTILATOR  = "ventilator"


class ConditionSeverity(str, Enum):
    """Triage severity level of the patient."""
    CRITICAL = "critical"   # Needs ICU + possibly ventilator
    SERIOUS  = "serious"    # Needs ICU, may not need ventilator
    MODERATE = "moderate"   # Standard bed, no ICU
    STABLE   = "stable"     # Minor — walk-in or basic care


# ─────────────────────────────────────────────
# PATIENT REQUEST SCHEMA
# ─────────────────────────────────────────────

@dataclass
class PatientRequest:
    """
    Represents a single emergency rescue request made by or for a patient.

    Fields:
        id                  : Unique request identifier (e.g., "REQ-001")
        location            : GPS coordinates [lat, lng] of the patient
        condition           : Free-text description of the emergency
        severity            : Triage level (ConditionSeverity enum)
        requires_icu        : True if patient needs ICU admission
        requires_ventilator : True if patient needs mechanical ventilation
        status              : Current lifecycle status (PatientStatus enum)
        assigned_ambulance  : ID of ambulance dispatched (None if pending)
        assigned_hospital   : ID of hospital selected (None if pending)
        confidence          : Confidence level of triage inference (0.0 to 1.0)
        explanation         : Reasoning for the assigned severity and resources
    """
    id:                  str
    location:            Tuple[float, float]        # (lat, lng)
    condition:           str
    severity:            ConditionSeverity
    requires_icu:        bool = False
    requires_ventilator: bool = False
    status:              PatientStatus = PatientStatus.PENDING
    assigned_ambulance:  Optional[str] = None
    assigned_hospital:   Optional[str] = None
    confidence:          float = 0.0
    explanation:         str = ""


# ─────────────────────────────────────────────
# AMBULANCE STATE SCHEMA
# ─────────────────────────────────────────────

@dataclass
class AmbulanceState:
    """
    Real-time state of a single ambulance unit.

    Fields:
        id                      : Unique ambulance ID (e.g., "AMB-01")
        current_coordinates     : Live GPS position [lat, lng]
        assigned_patient_id     : ID of patient being served (None if idle)
        destination_hospital_id : Target hospital ID (None if no assignment)
        route_polyline          : Ordered list of [lat, lng] waypoints for
                                  the active route. Empty if idle.
        is_available            : False when actively on a mission
    """
    id:                      str
    current_coordinates:     Tuple[float, float]    # (lat, lng)
    assigned_patient_id:     Optional[str] = None
    destination_hospital_id: Optional[str] = None
    route_polyline:          List[Tuple[float, float]] = field(default_factory=list)
    is_available:            bool = True


# ─────────────────────────────────────────────
# HOSPITAL SCHEMA
# ─────────────────────────────────────────────

@dataclass
class Hospital:
    """
    Represents a hospital node in the CIRO resource registry.

    Fields:
        id                  : Unique hospital identifier (e.g., "HOSP-A")
        name                : Full hospital name
        hospital_type       : Category (e.g., "Trauma Center", "General")
        coordinates         : GPS location (lat, lng)
        available_beds      : Standard beds currently free
        icu_beds            : ICU beds currently free
        ventilators         : Ventilators currently free
        contact_number      : Emergency contact phone number
        accepts_trauma      : True if hospital has trauma surgery capability
    """
    id:              str
    name:            str
    hospital_type:   str
    coordinates:     Tuple[float, float]
    available_beds:  int
    icu_beds:        int
    ventilators:     int
    contact_number:  str
    accepts_trauma:  bool = False


# ─────────────────────────────────────────────
# GLOBAL SHARED STATE
# ─────────────────────────────────────────────

@dataclass
class SystemState:
    """
    The single shared state object passed between all CIRO agents.

    This is the Antigravity-compatible 'world state' — every agent
    reads from and writes to this object during the pipeline run.

    Fields:
        patient_requests : All active/historical patient requests
        ambulances       : All ambulance units and their live states
        hospitals        : All hospital nodes with current resource counts
        event_log        : Timestamped agent reasoning trace (for dashboard)
    """
    patient_requests: List[PatientRequest]     = field(default_factory=list)
    ambulances:       List[AmbulanceState]     = field(default_factory=list)
    hospitals:        List[Hospital]           = field(default_factory=list)
    event_log:        List[dict]               = field(default_factory=list)
