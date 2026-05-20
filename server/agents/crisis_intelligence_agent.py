"""
=============================================================
CIRO — CrisisIntelligenceAgent
=============================================================
Agent #0 in the Antigravity pipeline.

Responsibility:
  - Ingests multi-source signals:
      • Social media posts (English + Urdu/Roman Urdu)
      • Weather API data (open-meteo)
      • Traffic congestion data (simulated)
  - Detects and classifies emerging crises
  - Estimates confidence level
  - Recommends coordinated response actions
  - Generates simulated execution plan

Supports Urdu, Roman Urdu, and English mixed inputs.
=============================================================
"""

import re
import os
import json
import random
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from shared.state_schema import SystemState

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)



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

# ── Urdu / Roman-Urdu Keyword Maps ───────────────────────────────────────────
URDU_FLOOD_KEYWORDS = [
    "pani", "bhar gaya", "barish", "sailaab", "toofan", "naala", "doob",
    "gharak", "baarish", "paani", "ubharna", "nikalna", "flooding"
]
URDU_FIRE_KEYWORDS = [
    "aag", "aag lag gayi", "dhuaan", "jalana", "jalna", "blast", "dhamaka",
    "sulag", "lahore", "fire", "burning", "blaze"
]
URDU_ACCIDENT_KEYWORDS = [
    "accident", "hadsa", "takkar", "gaari", "truck", "motorcyle", "crash",
    "tabah", "zakmi", "zakhmi", "lahoo", "khoon", "phans gayi"
]
URDU_HEATWAVE_KEYWORDS = [
    "garmi", "garm", "tapish", "luu", "heat", "behosh", "dehydration",
    "pyas", "bukhar", "sun stroke", "heatstroke", "temperature"
]
URDU_INFRASTRUCTURE_KEYWORDS = [
    "bijli", "batti", "current", "light chali gayi", "gas nahi", "paani nahi",
    "power failure", "blackout", "overpass", "pul", "bridge", "dhaancha"
]
URDU_LOCATION_MARKERS = [
    "mein", "pe", "par", "walay", "wali", "ki", "ka", "ke", "qareeb",
    "saman", "aas paas", "nazar aata", "ho raha hai", "ho rahi"
]


# ── English + Mixed Crisis Keyword Maps ──────────────────────────────────────
CRISIS_DETECTION_CONFIG = {
    "flood": {
        "en_keywords": ["flood", "flooding", "flash flood", "waterlogged", "water logging",
                        "drain overflow", "rain", "submerged", "stranded vehicles"],
        "ur_keywords": URDU_FLOOD_KEYWORDS,
        "severity_amplifiers": ["30 mins", "hour", "2 hours", "several", "badly", "badtareen"],
        "default_severity": "HIGH",
        "response_actions": [
            "Traffic rerouting via alternate roads activated",
            "Emergency rescue boats deployed to affected zones",
            "Public alerts broadcasted via SMS and radio",
            "NDMA notified for coordination",
            "Water pumping units dispatched",
            "Shelter camps identified at dry elevated zones"
        ],
        "urdu_alert": "سیلاب کا خطرہ! فوری طور پر محفوظ مقام پر جائیں۔",
        "icon": "🌊",
        "color": "blue"
    },
    "fire": {
        "en_keywords": ["fire", "blaze", "burning", "smoke", "explosion", "blast", "inferno"],
        "ur_keywords": URDU_FIRE_KEYWORDS,
        "severity_amplifiers": ["massive", "huge", "spreading", "badly", "out of control"],
        "default_severity": "CRITICAL",
        "response_actions": [
            "Fire brigade units dispatched from nearest station",
            "Road closures and evacuation zones established",
            "Gas supply to affected block shut down",
            "Ambulances placed on standby at perimeter",
            "Aerial water bombers requested if needed",
            "Traffic diverted away from fire zone"
        ],
        "urdu_alert": "آگ لگ گئی! فوری طور پر علاقہ خالی کریں۔",
        "icon": "🔥",
        "color": "red"
    },
    "accident": {
        "en_keywords": ["accident", "collision", "crash", "hit-and-run", "vehicle overturned",
                        "injured", "casualties", "blocked road"],
        "ur_keywords": URDU_ACCIDENT_KEYWORDS,
        "severity_amplifiers": ["multiple", "severe", "critical", "many", "head-on"],
        "default_severity": "HIGH",
        "response_actions": [
            "Trauma ambulances dispatched to accident site",
            "Police for traffic management notified",
            "Rescue 1122 / Edhi units dispatched",
            "Alternate traffic routes activated",
            "Nearest hospital ER placed on trauma standby",
            "Live map traffic alerts updated"
        ],
        "urdu_alert": "حادثہ رپورٹ ہوا! ایمبولینس روانہ کر دی گئی ہے۔",
        "icon": "🚗",
        "color": "amber"
    },
    "heatwave": {
        "en_keywords": ["heatwave", "heat stroke", "extreme heat", "dehydration", "sun stroke",
                        "temperature above 40", "heat emergency"],
        "ur_keywords": URDU_HEATWAVE_KEYWORDS,
        "severity_amplifiers": ["45 degrees", "46", "47", "extreme", "badtareen"],
        "default_severity": "MEDIUM",
        "response_actions": [
            "Cooling centers activated at public buildings",
            "Free water and ORS distribution points opened",
            "Hospitals alerted for heat emergency patient surge",
            "Outdoor work restrictions enforced 11am-3pm",
            "SMS alerts dispatched to vulnerable populations",
            "Water sprinkler systems activated on main roads"
        ],
        "urdu_alert": "شدید گرمی! پانی پیتے رہیں، دوپہر میں باہر نہ نکلیں۔",
        "icon": "☀️",
        "color": "orange"
    },
    "infrastructure": {
        "en_keywords": ["power failure", "blackout", "gas leak", "bridge collapse", "road collapse",
                        "overhead cable", "transformer explosion", "infrastructure failure"],
        "ur_keywords": URDU_INFRASTRUCTURE_KEYWORDS,
        "severity_amplifiers": ["complete", "entire area", "city wide", "hours", "since morning"],
        "default_severity": "MEDIUM",
        "response_actions": [
            "KESC / LESCO / WAPDA emergency team dispatched",
            "Generator backup activated at critical facilities",
            "Road safety barriers deployed around affected area",
            "Alternative routes activated for vehicle rerouting",
            "Emergency repair crews mobilized",
            "Public announcement via PEMRA channels broadcast"
        ],
        "urdu_alert": "بنیادی ڈھانچے کی خرابی! متعلقہ ادارے کو اطلاع دی گئی ہے۔",
        "icon": "⚡",
        "color": "purple"
    },
    "disinformation": {
        "en_keywords": [],
        "ur_keywords": [],
        "severity_amplifiers": [],
        "default_severity": "LOW",
        "response_actions": [
            "No action taken. Incident flagged as disinformation / false report.",
            "Disinformation warning broadcasted to local response network.",
            "Signal logs flagged in monitoring database."
        ],
        "urdu_alert": "جھوٹی خبر! کوئی ہنگامی صورتحال نہیں پائی گئی۔",
        "icon": "🚫",
        "color": "gray"
    }
}


def _detect_crisis_from_signal(text: str) -> Tuple[Optional[str], int, List[str]]:
    """
    Detects crisis type, matched keywords, and confidence score from a text signal.
    Handles mixed English/Urdu/Roman-Urdu.
    Returns: (crisis_type, confidence_score_pct, matched_keywords)
    """
    text_lower = text.lower()
    
    best_type = None
    best_score = 0
    best_matches = []

    for crisis_type, config in CRISIS_DETECTION_CONFIG.items():
        matches = []
        
        # Check English keywords
        for kw in config["en_keywords"]:
            if kw.lower() in text_lower:
                matches.append(kw)
        
        # Check Urdu keywords
        for kw in config["ur_keywords"]:
            if kw.lower() in text_lower:
                matches.append(kw)

        # Severity amplifier bonus
        amplifier_bonus = 0
        for amp in config["severity_amplifiers"]:
            if amp.lower() in text_lower:
                amplifier_bonus += 10

        score = len(matches) * 25 + amplifier_bonus
        if score > best_score:
            best_score = score
            best_type = crisis_type
            best_matches = matches

    confidence = min(best_score, 98)
    return best_type, confidence, best_matches


class CrisisIntelligenceAgent:
    """
    CIRO Antigravity Agent #0 — CrisisIntelligenceAgent

    Processes multi-source signals, detects crisis types, and generates
    coordinated response plans with full trace/decision logging.
    """

    def __init__(self, state: SystemState):
        self.state = state
        self.name = "CrisisIntelligenceAgent"

    def _log(self, message: str):
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "agent": self.name,
            "message": message
        }
        self.state.event_log.append(entry)
        try:
            print(f"  [{entry['timestamp']}] [{self.name}] {message}")
        except UnicodeEncodeError:
            safe_msg = message.encode("ascii", "replace").decode("ascii")
            print(f"  [{entry['timestamp']}] [{self.name}] {safe_msg}")

    def _simulate_weather_signal(self, city: str = "Karachi") -> Dict[str, Any]:
        """Fetches live weather API signal for the current city using Open-Meteo."""
        import requests
        try:
            # 1. Geocode the city
            url = f"https://nominatim.openstreetmap.org/search?q={city}, Pakistan&format=json&limit=1"
            headers = {"User-Agent": "CIRO-Antigravity-Agent/1.0"}
            res = requests.get(url, headers=headers, timeout=3)
            if res.status_code == 200 and len(res.json()) > 0:
                data = res.json()[0]
                lat, lon = float(data["lat"]), float(data["lon"])
                
                # 2. Get live weather
                w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,wind_speed_10m&timezone=auto"
                w_res = requests.get(w_url, timeout=3.0)
                if w_res.status_code == 200:
                    current = w_res.json().get("current", {})
                    temp = current.get("temperature_2m", 30.0)
                    precip = current.get("precipitation", 0.0)
                    wind = current.get("wind_speed_10m", 10.0)
                    
                    condition = "clear"
                    alert = "No active weather emergency"
                    if precip > 10.0:
                        condition = "heavy_rain"
                        alert = "Heavy Rain Advisory Active"
                    elif temp >= 40.0:
                        condition = "heatwave"
                        alert = "Extreme Heat Warning"
                        
                    return {
                        "condition": condition,
                        "rainfall_mm": precip,
                        "temp_c": temp,
                        "wind_kmh": wind,
                        "alert": alert,
                        "city": city
                    }
        except Exception as e:
            self._log(f"[WARNING] Live weather fetch failed: {e}. Using fallback simulation.")
            
        # Fallback
        import random
        scenarios = [
            {"condition": "heavy_rain", "rainfall_mm": random.randint(35, 80), "temp_c": random.randint(28, 33), "wind_kmh": random.randint(30, 60), "alert": "Heavy Rain Advisory Active"},
            {"condition": "heatwave", "rainfall_mm": 0, "temp_c": random.randint(42, 47), "wind_kmh": random.randint(5, 15), "alert": "Extreme Heat Warning"},
            {"condition": "clear", "rainfall_mm": 0, "temp_c": random.randint(32, 38), "wind_kmh": random.randint(10, 20), "alert": "No active weather emergency"},
        ]
        scenario = random.choice(scenarios)
        scenario["city"] = city
        return scenario

    def _simulate_traffic_signal(self) -> Dict[str, Any]:
        """Simulates a traffic API signal dynamically based on current time."""
        from datetime import datetime
        import random
        
        hour = datetime.now().hour
        # Rush hours: 8-10 AM, 5-8 PM
        is_rush_hour = (8 <= hour <= 10) or (17 <= hour <= 20)
        
        if is_rush_hour:
            congestion_level = random.choice(["severe", "critical"])
        elif 1 <= hour <= 5:
            congestion_level = "normal"
        else:
            congestion_level = random.choice(["normal", "moderate", "severe"])
            
        return {
            "congestion_level": congestion_level,
            "blocked_roads": random.randint(0, 5),
            "incidents_reported": random.randint(0, 3),
            "avg_speed_kmh": {"normal": 45, "moderate": 25, "severe": 12, "critical": 4}[congestion_level]
        }

    def analyze_signals(
        self,
        social_posts: List[str],
        city: str = "Karachi",
        include_weather: bool = True,
        include_traffic: bool = True
    ) -> Dict[str, Any]:
        """
        Main analysis pipeline. Ingests social posts + weather + traffic,
        detects crisis type, generates confidence score, and recommends actions.
        """
        self._log("=" * 60)
        self._log("CRISIS INTELLIGENCE PIPELINE INITIATED")
        self._log("=" * 60)

        # ── Phase 1: Multi-source ingestion & Satellite Verification ──
        self._log(f"Phase 1 — Ingesting {len(social_posts)} social signal(s)...")
        
        validated_signals = []
        valid_social_posts = []
        
        for i, post in enumerate(social_posts, 1):
            self._log(f"  📡 Signal [{i}]: {post[:80]}{'...' if len(post)>80 else ''}")
            is_valid = True
            reason = "Weather sensors corroborate report."
            detected_type = None
            landmark = ""
            explanation = ""
            
            # If API key is present, use Gemini to parse location and crisis type robustly
            if api_key:
                try:
                    self._log(f"    Analyzing signal [{i}] with Gemini AI model...")
                    model = genai.GenerativeModel("gemini-3.5-flash")
                    prompt = f'''
Analyze the following social media post/signal reporting a crisis in {city}:
"{post}"

Extract the following details and return ONLY a valid JSON object. Do not include markdown formatting or backticks.
{{
  "landmark": "string, the specific location/landmark if mentioned in the text (e.g. Clifton 5, M2 motorway, Orangi Town, G-10), otherwise empty string",
  "landmark_english_geocodable": "string, a standardized English translation/transliteration of the landmark suitable for OpenStreetMap search (e.g. 'Baloch Colony Flyover' for 'balouch ka pull', 'Teen Talwar Clifton' for 'teen talwar Clifton'), otherwise empty string",
  "crisis_type": "string, one of: flood, fire, accident, heatwave, infrastructure, general",
  "explanation": "string, short translation/explanation of the signal"
}}
'''
                    response = model.generate_content(prompt)
                    text_response = response.text.replace("```json", "").replace("```", "").strip()
                    res_json = json.loads(text_response)
                    
                    landmark = res_json.get("landmark_english_geocodable", "") or res_json.get("landmark", "")
                    detected_type = res_json.get("crisis_type", "general")
                    explanation = res_json.get("explanation", "")
                    self._log(f"      Gemini extracted landmark: '{landmark}' | Type: {detected_type.upper()}")
                except Exception as e:
                    self._log(f"      Gemini extraction error: {e}. Falling back to offline parsing.")
            
            if not detected_type or detected_type == "general":
                # Fallback to regex & keyword detection
                detected_type, _, matched_kws = _detect_crisis_from_signal(post)
                
                # Extract location from post via regex
                match_en = re.search(r'\b(?:near|at|in|qareeb|mein|mai|main)\s+([A-Za-z0-9\s\-]+?)(?:,|\.|requires|needs|immediately|!|\bfor\b|$)', post, re.IGNORECASE)
                if match_en:
                    landmark = match_en.group(1).strip()
                else:
                    match_ur = re.search(r'([A-Za-z0-9\s\-]+?)\s+(?:mein|mai|main|ke\s+qareeb|qareeb|pe|par)\b', post, re.IGNORECASE)
                    if match_ur:
                        landmark = match_ur.group(1).strip()

            # Clean punctuation
            if landmark:
                landmark = re.sub(r'[^\w\s\-]', '', landmark).strip()
            else:
                # Default to city name if no landmark found
                landmark = city

            # If it's a flood or heatwave report, query weather at the location
            coords = None
            if detected_type in ["flood", "heatwave"]:
                try:
                    # Clean landmark lower for dict lookup
                    landmark_lower = landmark.lower()
                    local_hit = None
                    if landmark_lower in LOCAL_KARACHI_LOCATIONS:
                        local_hit = LOCAL_KARACHI_LOCATIONS[landmark_lower]
                    else:
                        norm = landmark_lower.replace("colony", "").replace("bridge", "").replace("flyover", "").replace("pull", "").replace("chowrangi", "").replace("chaurangi", "").replace("road", "").replace("building", "").strip()
                        if norm in LOCAL_KARACHI_LOCATIONS:
                            local_hit = LOCAL_KARACHI_LOCATIONS[norm]
                        else:
                            for key, l_coords in LOCAL_KARACHI_LOCATIONS.items():
                                if key in landmark_lower or landmark_lower in key:
                                    local_hit = l_coords
                                    break
                                    
                    if local_hit:
                        coords = local_hit
                        self._log(f"      [LOCAL DICTIONARY HIT] Geocoded '{landmark}' -> {coords}")
                    else:
                        query = f"{landmark}, {city}, Pakistan" if city.lower() not in landmark.lower() else f"{landmark}, Pakistan"
                        self._log(f"    Verifying signal [{i}] location '{landmark}' against live satellites...")
                        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
                        headers = {"User-Agent": "CIRO-Antigravity-Agent/1.0"}
                        res = requests.get(url, headers=headers, timeout=3)
                        
                        # Fallback to city coordinates if landmark geocoding fails
                        if res.status_code != 200 or len(res.json()) == 0:
                            self._log(f"      Landmark '{landmark}' not found. Falling back to city '{city}' coordinates...")
                            query = f"{city}, Pakistan"
                            res = requests.get(f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1", headers=headers, timeout=3)
                            
                        if res.status_code == 200 and len(res.json()) > 0:
                            data = res.json()[0]
                            coords = (float(data["lat"]), float(data["lon"]))
                        else:
                            self._log(f"      Nominatim could not locate '{landmark}' or '{city}'. Verification skipped.")

                    if coords:
                        # Query weather
                        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={coords[0]}&longitude={coords[1]}&current=temperature_2m,precipitation&timezone=auto"
                        w_res = requests.get(w_url, timeout=3.0)
                        if w_res.status_code == 200:
                            w_data = w_res.json().get("current", {})
                            temp = w_data.get("temperature_2m", 0.0)
                            precip = w_data.get("precipitation", 0.0)
                            
                            self._log(f"      Satellite check at {landmark} -> Temp: {temp}°C | Precipitation: {precip}mm")
                            
                            if detected_type == "heatwave" and temp < 38.0:
                                is_valid = False
                                reason = f"FAKE NEWS: Reported heatwave, but live satellite temperature at {landmark} is only {temp}°C (threshold: >= 38.0°C)."
                            elif detected_type == "flood" and precip < 2.0:
                                is_valid = False
                                reason = f"FAKE NEWS: Reported flooding/rain, but live satellite precipitation at {landmark} is only {precip}mm (threshold: >= 2.0mm)."
                        else:
                            self._log("      Weather API error during verification. Assuming signal is valid.")
                except Exception as e:
                    self._log(f"      Signal validation error: {e}. Skipping verification.")
            
            if not is_valid:
                self._log(f"    ❌ Signal [{i}] flagged as FALSE INFO: {reason}")
            else:
                self._log(f"    ✅ Signal [{i}] verified successfully.")
                valid_social_posts.append(post)
                
            validated_signals.append({
                "post": post,
                "is_valid": is_valid,
                "reason": reason,
                "location": landmark or city,
                "coordinates": coords
            })

        weather = {}
        if include_weather:
            self._log(f"Phase 1 — Polling weather API for {city}...")
            weather = self._simulate_weather_signal(city)
            self._log(f"  🌡 Weather: {weather['condition'].upper()} | Temp: {weather['temp_c']}°C | Rain: {weather['rainfall_mm']}mm | {weather['alert']}")

        traffic = {}
        if include_traffic:
            self._log("Phase 1 — Polling traffic congestion API...")
            traffic = self._simulate_traffic_signal()
            self._log(f"  🚦 Traffic: {traffic['congestion_level'].upper()} congestion | Avg speed: {traffic['avg_speed_kmh']} km/h | Blocked roads: {traffic['blocked_roads']}")

        # ── Phase 2: Signal fusion & crisis detection ─────────────────
        self._log("Phase 2 — Running multi-signal fusion and crisis detection...")

        all_signals_text = " ".join(valid_social_posts) if valid_social_posts else ""
        
        if not all_signals_text:
            crisis_type = "disinformation"
            base_confidence = 0
            matched_keywords = ["all signals flagged as fake news"]
            self._log("  ❌ Crisis Detected: [DISINFORMATION] | Confidence: 100% | All signals flagged as fake news.")
        else:
            crisis_type, base_confidence, matched_keywords = _detect_crisis_from_signal(all_signals_text)

        # Boost confidence from corroborating weather/traffic signals
        weather_boost = 0
        if weather and crisis_type != "disinformation":
            if crisis_type == "flood" and weather.get("condition") == "heavy_rain":
                weather_boost = 20
                self._log("  🔗 Corroborating weather signal: Heavy rain confirms flood crisis → +20% confidence")
            elif crisis_type == "heatwave" and weather.get("temp_c", 0) >= 42:
                weather_boost = 25
                self._log(f"  🔗 Corroborating weather signal: {weather['temp_c']}°C extreme temp confirms heatwave → +25% confidence")

        traffic_boost = 0
        if traffic and crisis_type != "disinformation":
            if traffic["congestion_level"] in ("severe", "critical") and crisis_type in ("flood", "accident"):
                traffic_boost = 15
                self._log(f"  🔗 Corroborating traffic signal: {traffic['congestion_level']} congestion confirms {crisis_type} impact → +15% confidence")

        if crisis_type == "disinformation":
            final_confidence = 100
        else:
            final_confidence = min(base_confidence + weather_boost + traffic_boost, 99)

        if crisis_type is None:
            crisis_type = "accident"
            final_confidence = 45
            matched_keywords = ["unclassified signal"]
            self._log("  ⚠ No definitive crisis pattern detected — defaulting to unclassified emergency")
        elif crisis_type != "disinformation":
            self._log(f"  ✅ Crisis Detected: [{crisis_type.upper()}] | Confidence: {final_confidence}% | Matched signals: {matched_keywords}")

        # ── Phase 3: Situation analysis ───────────────────────────────
        self._log("Phase 3 — Synthesizing situation assessment...")

        config = CRISIS_DETECTION_CONFIG.get(crisis_type, CRISIS_DETECTION_CONFIG["accident"])
        severity = config["default_severity"]
        if final_confidence >= 85:
            severity = "CRITICAL" if crisis_type in ("fire", "flood") else "HIGH"

        impact_map = {
            "flood": ["Traffic blocked on major arteries", "Vehicles stranded in flood zones",
                      "Risk of drowning for pedestrians", "Infrastructure damage possible"],
            "fire":  ["Evacuations required in 500m radius", "Road closures imminent",
                      "Risk of fire spreading to adjacent buildings", "Gas explosion risk"],
            "accident": ["Lane blockage reducing road capacity", "Emergency services required",
                         "Potential multi-casualty event", "Traffic delays 3-5km range"],
            "heatwave": ["Vulnerable populations at risk", "Heat stroke cases expected at hospitals",
                         "Outdoor workers at danger", "Water shortages possible"],
            "infrastructure": ["Power/utility outage affecting thousands", "Critical facilities impacted",
                                "Business and hospital backup power needed", "Public services disrupted"]
        }

        impacts = impact_map.get(crisis_type, ["Unknown impact zone"])
        self._log(f"  📊 Severity Assessment: {severity}")
        for imp in impacts:
            self._log(f"  ⚠ Impact: {imp}")

        # ── Phase 4: Action planning ──────────────────────────────────
        self._log("Phase 4 — Generating coordinated response action plan...")
        actions = config["response_actions"]
        for i, action in enumerate(actions, 1):
            self._log(f"  📋 Action [{i}]: {action}")

        # ── Phase 5: Simulated execution ──────────────────────────────
        self._log("Phase 5 — Simulating execution of response actions...")
        execution_log = self._simulate_execution(crisis_type, actions, city)

        # Build result
        result = {
            "crisis_type": crisis_type,
            "confidence": final_confidence,
            "severity": severity,
            "city": city,
            "matched_signals": matched_keywords,
            "weather_signal": weather,
            "traffic_signal": traffic,
            "impacts": impacts,
            "response_actions": actions,
            "execution_log": execution_log,
            "urdu_alert": config["urdu_alert"],
            "icon": config["icon"],
            "color": config["color"],
            "social_posts": social_posts,
            "validated_signals": validated_signals,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "before_state": {
                "traffic_flow": "Normal",
                "emergency_resources": "Standby",
                "public_alerts": "None",
                "congestion_index": traffic.get("blocked_roads", 0)
            },
            "after_state": {
                "traffic_flow": "Rerouted via alternate corridors",
                "emergency_resources": "Fully Deployed",
                "public_alerts": "Broadcast on SMS, Radio, Map",
                "congestion_index": max(0, traffic.get("blocked_roads", 0) - 3)
            }
        }

        self._log("=" * 60)
        self._log(f"CRISIS INTELLIGENCE COMPLETE — {crisis_type.upper()} | {final_confidence}% confidence")
        self._log("=" * 60)

        return result

    def _simulate_execution(self, crisis_type: str, actions: List[str], city: str) -> List[Dict]:
        """Simulates the execution of each response action."""
        execution_log = []
        
        for action in actions:
            delay_ms = random.randint(120, 800)
            execution_log.append({
                "action": action,
                "status": "EXECUTED",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "simulated_delay_ms": delay_ms,
                "notes": f"Simulated execution in {delay_ms}ms — {city} coordination confirmed"
            })
            self._log(f"  ✅ EXECUTED [{delay_ms}ms]: {action[:60]}")

        return execution_log
