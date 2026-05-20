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

Design: Gemini LLM + Geocoding API with Keyword fallback.
=============================================================
"""

import re
import os
import json
from typing import Tuple, Optional
from datetime import datetime
from shared.state_schema import (
    PatientRequest, PatientStatus, ConditionSeverity, SystemState
)

import requests
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# ─── Crisis type keyword mapping (Fallback) ────────────────────────
CRISIS_KEYWORDS = {
    "accident":   ["accident", "crash", "collision", "hit", "road", "vehicle"],
    "flood":      ["flood", "pani", "drowning", "water", "bhar gaya", "barish"],
    "fire":       ["fire", "aag", "burning", "smoke", "blast", "explosion"],
    "heatwave":   ["heat", "heatstroke", "dehydration", "temperature", "garmi"],
    "cardiac":    ["heart", "cardiac", "chest pain", "attack", "stroke"],
    "trauma":     ["bleeding", "injury", "fracture", "stab", "shot", "wound"],
}

# ─── Resource need keywords (Fallback) ──────────────────────────────
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

# ─── Local Karachi Location Coordinates ─────────────────────────────
LOCAL_KARACHI_LOCATIONS = {
    "balouch ka pull": (24.8533, 67.0682),
    "baloch colony bridge": (24.8533, 67.0682),
    "baloch colony flyover": (24.8533, 67.0682),
    "baloch colony pull": (24.8533, 67.0682),
    "balouch colony pull": (24.8533, 67.0682),
    "baloch bridge": (24.8533, 67.0682),
    "balouch bridge": (24.8533, 67.0682),
    "baloch colony": (24.8533, 67.0682),
    "balouch colony": (24.8533, 67.0682),
    "teen talwar": (24.8236, 67.0329),
    "do talwar": (24.8219, 67.0305),
    "stadium road": (24.8942, 67.0789),
    "national stadium": (24.8942, 67.0789),
    "clifton 5": (24.8268, 67.0264),
    "clifton block 5": (24.8268, 67.0264),
    "clifton": (24.8268, 67.0264),
    "ftc": (24.8569, 67.0531),
    "ftc building": (24.8569, 67.0531),
    "nipa": (24.9179, 67.0972),
    "nipa chowrangi": (24.9179, 67.0972),
    "nipa chaurangi": (24.9179, 67.0972),
    "numaish": (24.8732, 67.0322),
    "numaish chowrangi": (24.8732, 67.0322),
    "numaish chaurangi": (24.8732, 67.0322),
    "karsaz": (24.8872, 67.0872),
    "karsaz road": (24.8872, 67.0872),
    "gulshan": (24.9180, 67.0970),
    "gulshan-e-iqbal": (24.9180, 67.0970),
    "gulshan iqbal": (24.9180, 67.0970),
    "saddar": (24.8605, 67.0261),
    "i.i. chundrigar": (24.8505, 67.0016),
    "chundrigar road": (24.8505, 67.0016),
    "ii chundrigar": (24.8505, 67.0016),
    "water pump": (24.9455, 67.0792),
    "sohrab goth": (24.9601, 67.0873),
    "nazimabad": (24.9137, 67.0343),
    "liaquatabad": (24.9088, 67.0427),
    "bahadurabad": (24.8824, 67.0664),
    "tariq road": (24.8705, 67.0543),
    "dha": (24.8010, 67.0673),
    "orangi": (24.9463, 66.9749),
    "korangi": (24.8360, 67.1265),
    "malir": (24.9056, 67.1973),
    "shahrah-e-faisal": (24.8660, 67.0768),
    "shara-e-faisal": (24.8660, 67.0768),
    "university road": (24.9142, 67.1089)
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
    def _extract_coordinates(self, text: str, skip_regex: bool = False, city_context: str = "") -> Tuple[float, float]:
        """Live Geocoding fallback using OpenStreetMap Nominatim API"""
        self._log("Attempting live geocoding via OpenStreetMap API...")
        
        landmark = ""
        if not skip_regex:
            # 1. Match "near/at/in [Landmark]" (English / Roman Urdu)
            match_en = re.search(r'\b(?:near|at|in|qareeb|mein|mai|main)\s+([A-Za-z0-9\s\-]+?)(?:,|\.|requires|needs|immediately|!|\bfor\b|$)', text, re.IGNORECASE)
            if match_en:
                landmark = match_en.group(1).strip()
            else:
                # 2. Match "[Landmark] mein/qareeb" (Roman Urdu/Urdu)
                match_ur = re.search(r'([A-Za-z0-9\s\-]+?)\s+(?:mein|mai|main|ke\s+qareeb|qareeb|pe|par)\b', text, re.IGNORECASE)
                if match_ur:
                    landmark = match_ur.group(1).strip()
            
            if not landmark:
                # Fallback to taking the last few words
                words = text.split()
                landmark = " ".join(words[-3:]) if len(words) >= 3 else text
        else:
            landmark = text
            
        # Clean any punctuation
        landmark = re.sub(r'[^\w\s\-]', '', landmark).strip()
        
        # Check local dictionary first
        landmark_lower = landmark.lower()
        if landmark_lower in LOCAL_KARACHI_LOCATIONS:
            coords = LOCAL_KARACHI_LOCATIONS[landmark_lower]
            self._log(f"[LOCAL DICTIONARY HIT] Resolved '{landmark}' to {coords}")
            return coords
            
        # Standardize common variations before checking
        norm = landmark_lower.replace("colony", "").replace("bridge", "").replace("flyover", "").replace("pull", "").replace("chowrangi", "").replace("chaurangi", "").replace("road", "").replace("building", "").strip()
        if norm in LOCAL_KARACHI_LOCATIONS:
            coords = LOCAL_KARACHI_LOCATIONS[norm]
            self._log(f"[LOCAL DICTIONARY NORM HIT] Resolved '{landmark}' to {coords}")
            return coords

        for key, coords in LOCAL_KARACHI_LOCATIONS.items():
            if key in landmark_lower or landmark_lower in key:
                self._log(f"[LOCAL DICTIONARY PARTIAL HIT] Resolved '{landmark}' to {coords} via key '{key}'")
                return coords
        
        try:
            if city_context:
                query = f"{landmark}, {city_context}, Pakistan"
            else:
                query = f"{landmark}, Karachi, Pakistan" if "karachi" not in landmark.lower() and "lahore" not in landmark.lower() and "islamabad" not in landmark.lower() else f"{landmark}, Pakistan"
            
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

    # -- Crisis type detector (Fallback) -----------------------------
    def _detect_crisis_type(self, text: str) -> str:
        text_lower = text.lower()
        for crisis_type, keywords in CRISIS_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    self._log(f"Crisis type matched: '{kw}' -> [{crisis_type.upper()}]")
                    return crisis_type
        self._log("Crisis type: [GENERAL EMERGENCY] (no specific keyword matched)")
        return "general"

    # -- Resource needs detector (Fallback) --------------------------
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
        if not request_id:
            request_id = f"REQ-{len(self.state.patient_requests) + 1:03d}"

        self._log("=" * 55)
        self._log(f"NEW EMERGENCY TRIGGER RECEIVED")
        self._log(f"Request ID : {request_id}")
        self._log(f"Raw Input  : \"{raw_text}\"")
        self._log("=" * 55)
        
        llm_success = False
        crisis_type = "general"
        needs_icu = False
        needs_vent = False
        severity = ConditionSeverity.MODERATE
        confidence_score = 0.5
        explanation_text = ""
        coords = (24.8607, 67.0011)

        # 1. Try LLM if API Key is configured
        if api_key:
            self._log("Step 1 - Using Gemini AI Model to deeply analyze multilingual text...")
            try:
                model = genai.GenerativeModel("gemini-3.5-flash")
                prompt = f'''
Analyze the following emergency text which could be in English, Urdu, or Roman Urdu.
Text: "{raw_text}"

Extract the following details and return ONLY a valid JSON object. Do not include markdown formatting or backticks.
{{
  "landmark": "string, the specific location/landmark if mentioned in original text, otherwise empty string",
  "city": "string, the city name if mentioned or implied (e.g. Islamabad, Karachi, Lahore), otherwise empty string",
  "landmark_english_geocodable": "string, a standardized English translation/transliteration of the landmark suitable for OpenStreetMap search (e.g. 'G-10 Markaz' for 'g10', 'Baloch Colony Flyover' for 'balouch ka pull', 'Teen Talwar Clifton' for 'teen talwar Clifton'), otherwise empty string",
  "crisis_type": "string, one of: flood, fire, accident, heatwave, cardiac, trauma, general",
  "requires_icu": true or false based on critical condition/bleeding/unconscious,
  "requires_ventilator": true or false based on breathing issues,
  "severity": "string, one of: critical, severe, moderate, stable",
  "explanation": "string, a short explanation of the emergency based on text"
}}
'''
                response = model.generate_content(prompt)
                text_response = response.text.replace("```json", "").replace("```", "").strip()
                result = json.loads(text_response)
                
                landmark_text = result.get("landmark", "")
                city_text = result.get("city", "")
                landmark_geo = result.get("landmark_english_geocodable", "")
                crisis_type = result.get("crisis_type", "general")
                needs_icu = result.get("requires_icu", False)
                needs_vent = result.get("requires_ventilator", False)
                sev_str = result.get("severity", "moderate").lower()
                explanation_text = result.get("explanation", "Processed by AI model.")
                confidence_score = 0.98
                
                if sev_str == "critical": severity = ConditionSeverity.CRITICAL
                elif sev_str == "severe": severity = ConditionSeverity.SERIOUS
                elif sev_str == "stable": severity = ConditionSeverity.STABLE
                else: severity = ConditionSeverity.MODERATE
                
                # Coordinate matching
                resolved_via_ai = False
                if landmark_geo:
                    self._log(f"LLM extracted standardized landmark: '{landmark_geo}' in city '{city_text}'. Resolving on map...")
                    extracted_coords = self._extract_coordinates(landmark_geo, skip_regex=True, city_context=city_text)
                    if extracted_coords != (24.8607, 67.0011):
                        coords = extracted_coords
                        resolved_via_ai = True
                        self._log(f"AI Location override successful (standardized): {coords}")
                        
                if not resolved_via_ai and landmark_text:
                    self._log(f"LLM extracted raw landmark: '{landmark_text}' in city '{city_text}'. Resolving on map...")
                    extracted_coords = self._extract_coordinates(landmark_text, skip_regex=True, city_context=city_text)
                    if extracted_coords != (24.8607, 67.0011):
                        coords = extracted_coords
                        resolved_via_ai = True
                        self._log(f"AI Location override successful (raw): {coords}")
                        
                if not resolved_via_ai:
                    if live_coords:
                        self._log("No landmark geocoded by AI. Defaulting to device GPS.")
                        coords = live_coords
                    else:
                        self._log("No landmark geocoded by AI and no device GPS. Defaulting to Karachi center.")
                        coords = (24.8607, 67.0011)

                llm_success = True
            except Exception as e:
                self._log(f"LLM Integration Error: {e}. Falling back to offline dictionary mode...")
        else:
            self._log("LLM API key missing. Falling back to offline dictionary mode...")

        # 2. Offline Fallback Logic
        if not llm_success:
            self._log("Step 1 - Extracting location coordinates via NLP regex...")
            extracted_coords = self._extract_coordinates(raw_text)
            
            if extracted_coords == (24.8607, 67.0011) and live_coords:
                self._log(f"No specific landmark found in text. Falling back to Device GPS Provided: {live_coords}")
                coords = live_coords
            elif live_coords and extracted_coords != (24.8607, 67.0011):
                self._log(f"Text landmark detected! Overriding Device GPS with NLP coordinates: {extracted_coords}")
                coords = extracted_coords
            else:
                coords = extracted_coords

            self._log("Step 2 - Detecting crisis type...")
            crisis_type  = self._detect_crisis_type(raw_text)
            
            self._log("Step 3 - Evaluating resource requirements...")
            needs_icu    = self._check_requires_icu(raw_text)
            needs_vent   = self._check_requires_ventilator(raw_text)
            severity     = self._determine_severity(needs_icu, needs_vent, raw_text)
            confidence_score = self._calculate_confidence(raw_text, crisis_type)
            explanation_text = self._generate_explanation(severity, needs_icu, needs_vent, crisis_type)

        # 3. Satellite Weather Fraud Check
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
