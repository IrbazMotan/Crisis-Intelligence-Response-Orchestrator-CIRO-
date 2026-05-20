"""
=============================================================
CIRO — TriageAgent
=============================================================
Agent #1 in the Antigravity pipeline.

Responsibility:
  Ingests raw unstructured emergency text and extracts:
    - Emergency type
    - Patient GPS coordinates (from location name)
    - Whether ICU is required
    - Whether a Ventilator is required
    - Condition severity

Design: Keyword-based NLP + geocoding dictionary.
        (Can be swapped for Gemini API call in production)
=============================================================
"""

import re
from typing import Tuple, Optional
from datetime import datetime
from shared.state_schema import (
    PatientRequest, PatientStatus, ConditionSeverity, SystemState
)


import requests

# ─── Crisis type keyword mapping ───────────────────────────────────
CRISIS_KEYWORDS = {
    "accident":   ["accident", "crash", "collision", "hit", "road", "vehicle"],
    "flood":      ["flood", "pani", "drowning", "water", "bhar gaya", "barish"],
    "fire":       ["fire", "aag", "burning", "smoke", "blast", "explosion"],
    "heatwave":   ["heat", "heatstroke", "dehydration", "temperature", "garmi"],
    "cardiac":    ["heart", "cardiac", "chest pain", "attack", "stroke"],
    "trauma":     ["bleeding", "injury", "fracture", "stab", "shot", "wound"],
}

# ─── Resource need keywords ─────────────────────────────────────────
ICU_KEYWORDS         = ["icu", "critical", "unconscious", "severe", "bleeding heavily",
                        "cardiac", "stroke", "trauma", "not breathing", "intensive"]
VENTILATOR_KEYWORDS  = ["ventilator", "not breathing", "respiratory", "airway",
                        "suffocating", "choking", "intubate", "oxygen"]
SEVERITY_MAP = {
    "critical": ConditionSeverity.CRITICAL,
    "severe":   ConditionSeverity.SERIOUS,
    "moderate": ConditionSeverity.MODERATE,
    "stable":   ConditionSeverity.STABLE,
}


class TriageAgent:
    """
    Antigravity Agent #1 — TriageAgent

    Input : Raw emergency text string
    Output: Populated PatientRequest added to SystemState
    """

    def __init__(self, state: SystemState):
        self.state = state
        self.name  = "TriageAgent"

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

    # -- Geocoder --------------------------------------------------
    def _extract_coordinates(self, text: str) -> Tuple[float, float]:
        """Live Geocoding fallback using OpenStreetMap Nominatim API"""
        self._log("Attempting live geocoding via OpenStreetMap API...")
        
        # Robust regex-based landmark extraction
        landmark = ""
        # 1. Match "near/at/in [Landmark]" (English / Roman Urdu)
        match_en = re.search(r'\b(?:near|at|in|qareeb|mein)\s+([A-Za-z0-9\s\-]+?)(?:,|\.|requires|needs|immediately|!|\bfor\b|$)', text, re.IGNORECASE)
        if match_en:
            landmark = match_en.group(1).strip()
        else:
            # 2. Match "[Landmark] mein/qareeb" (Roman Urdu/Urdu)
            match_ur = re.search(r'([A-Za-z0-9\s\-]+?)\s+(?:mein|ke\s+qareeb|qareeb|pe|par)\b', text, re.IGNORECASE)
            if match_ur:
                landmark = match_ur.group(1).strip()
        
        if not landmark:
            # Fallback to taking the last few words, but clean it up
            words = text.split()
            landmark = " ".join(words[-3:]) if len(words) >= 3 else text
            
        # Clean any punctuation
        landmark = re.sub(r'[^\w\s\-]', '', landmark).strip()
        
        try:
            query = f"{landmark}, Karachi, Pakistan" if "karachi" not in landmark.lower() else f"{landmark}, Pakistan"
            self._log(f"Extracted landmark: '{landmark}' -> Querying Nominatim for: '{query}'")
            url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
            headers = {"User-Agent": "CIRO-Antigravity-Agent/1.0"}
            
            response = requests.get(url, headers=headers, timeout=3)
            if response.status_code == 200 and len(response.json()) > 0:
                data = response.json()[0]
                lat, lon = float(data["lat"]), float(data["lon"])
                self._log(f"[LIVE API SUCCESS] Geocoded '{data.get('name', 'location')}' -> ({lat}, {lon})")
                return (lat, lon)
        except Exception as e:
            self._log(f"[LIVE API ERROR] Geocoding failed: {e}")
            
        self._log("Live Geocoding API failed or found no results - defaulting to Karachi city center")
        return (24.8607, 67.0011)

    # -- Crisis type detector ---------------------------------------
    def _detect_crisis_type(self, text: str) -> str:
        text_lower = text.lower()
        for crisis_type, keywords in CRISIS_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    self._log(f"Crisis type matched: '{kw}' -> [{crisis_type.upper()}]")
                    return crisis_type
        self._log("Crisis type: [GENERAL EMERGENCY] (no specific keyword matched)")
        return "general"

    # -- Resource needs detector ------------------------------------
    def _check_requires_icu(self, text: str) -> bool:
        text_lower = text.lower()
        for kw in ICU_KEYWORDS:
            if kw in text_lower:
                self._log(f"ICU requirement flagged by keyword: '{kw}'")
                return True
        return False

    def _check_requires_ventilator(self, text: str) -> bool:
        text_lower = text.lower()
        for kw in VENTILATOR_KEYWORDS:
            if kw in text_lower:
                self._log(f"Ventilator requirement flagged by keyword: '{kw}'")
                return True
        return False

    def _determine_severity(self, requires_icu: bool, requires_ventilator: bool, text: str) -> ConditionSeverity:
        text_lower = text.lower()
        if requires_ventilator:
            return ConditionSeverity.CRITICAL
        if requires_icu:
            return ConditionSeverity.SERIOUS
        for word, severity in SEVERITY_MAP.items():
            if word in text_lower:
                return severity
        return ConditionSeverity.MODERATE

    def _generate_explanation(self, severity: ConditionSeverity, requires_icu: bool, requires_ventilator: bool, crisis_type: str) -> str:
        reasons = [f"Detected crisis type: {crisis_type.upper()}."]
        if requires_ventilator:
            reasons.append("Patient requires ventilator support indicating severe respiratory failure.")
        if requires_icu:
            reasons.append("Patient requires ICU admission for critical monitoring.")
        
        reasons.append(f"Severity classified as {severity.name} based on keyword analysis.")
        return " ".join(reasons)
        
    def _calculate_confidence(self, raw_text: str, crisis_type: str) -> float:
        text_lower = raw_text.lower()
        confidence = 0.5 # baseline
        
        if crisis_type != "general":
            confidence += 0.2
            
        for kw in ICU_KEYWORDS + VENTILATOR_KEYWORDS + list(SEVERITY_MAP.keys()):
            if kw in text_lower:
                confidence += 0.1
                
        return min(0.98, round(confidence, 2))

    # -- Main entry point -------------------------------------------
    def run(self, raw_text: str, request_id: str = None, live_coords: Tuple[float, float] = None) -> PatientRequest:
        """
        Processes raw emergency trigger text and creates a PatientRequest.

        Args:
            raw_text:    Unstructured emergency description
            request_id:  Optional ID; auto-generated if not provided
            live_coords: Exact GPS coordinates from device (Optional)

        Returns:
            PatientRequest added to SystemState
        """
        if not request_id:
            request_id = f"REQ-{len(self.state.patient_requests) + 1:03d}"

        self._log("=" * 55)
        self._log(f"NEW EMERGENCY TRIGGER RECEIVED")
        self._log(f"Request ID : {request_id}")
        self._log(f"Raw Input  : \"{raw_text}\"")
        self._log("=" * 55)
        
        if live_coords:
            self._log(f"Step 1 - High-Accuracy Device GPS Provided: {live_coords}")
            coords = live_coords
        else:
            self._log("Step 1 - Extracting location coordinates via NLP...")
            coords = self._extract_coordinates(raw_text)

        self._log("Step 2 - Detecting crisis type...")
        crisis_type  = self._detect_crisis_type(raw_text)

        # Satellite Weather Fraud Check
        is_fraud = False
        fraud_reason = ""
        if coords and crisis_type in ["flood", "heatwave"]:
            self._log(f"Validating real-time weather signals at {coords} via Open-Meteo satellite API...")
            try:
                lat, lon = coords
                url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation&timezone=auto"
                res = requests.get(url, timeout=3.0)
                if res.status_code == 200:
                    wdata = res.json().get("current", {})
                    temp = wdata.get("temperature_2m", 0.0)
                    precip = wdata.get("precipitation", 0.0)
                    self._log(f"  Live Weather Sensor -> Temperature: {temp}°C | Precipitation: {precip}mm")
                    
                    if crisis_type == "heatwave" and temp < 38.0:
                        is_fraud = True
                        fraud_reason = f"SECURITY WARNING: FRAUDULENT EMERGENCY. Reported heatwave, but live satellite temperature is only {temp}°C (threshold: >= 38.0°C)."
                    elif crisis_type == "flood" and precip < 2.0:
                        is_fraud = True
                        fraud_reason = f"SECURITY WARNING: FRAUDULENT EMERGENCY. Reported urban flooding, but live satellite precipitation is only {precip}mm (threshold: >= 2.0mm)."
            except Exception as e:
                self._log(f"Weather sensor API error: {e}. Skipping telemetry validation.")

        if is_fraud:
            self._log(f"[FRAUD DETECTED] {fraud_reason}")
            confidence_score = 0.0
            severity = ConditionSeverity.STABLE
            explanation_text = fraud_reason
            needs_icu = False
            needs_vent = False
        else:
            self._log("Step 3 - Evaluating resource requirements...")
            needs_icu    = self._check_requires_icu(raw_text)
            needs_vent   = self._check_requires_ventilator(raw_text)
            severity     = self._determine_severity(needs_icu, needs_vent, raw_text)
            confidence_score = self._calculate_confidence(raw_text, crisis_type)
            explanation_text = self._generate_explanation(severity, needs_icu, needs_vent, crisis_type)

        self._log(f"Triage Complete -> Severity: {severity.value.upper()} | "
                  f"ICU: {needs_icu} | Ventilator: {needs_vent}")

        self._log(f"Reasoning Explanation: {explanation_text}")
        self._log(f"Confidence Level: {confidence_score * 100}%")

        patient = PatientRequest(
            id                  = request_id,
            location            = coords,
            condition           = f"{crisis_type.title()} - {raw_text[:80]}",
            severity            = severity,
            requires_icu        = needs_icu,
            requires_ventilator = needs_vent,
            status              = PatientStatus.REJECTED if is_fraud else PatientStatus.PENDING,
            confidence          = confidence_score,
            explanation         = explanation_text
        )

        self.state.patient_requests.append(patient)
        self._log(f"PatientRequest [{request_id}] created and added to SystemState. Status: {patient.status.value.upper()}")
        return patient
