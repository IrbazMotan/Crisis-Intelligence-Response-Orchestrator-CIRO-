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
import random
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from shared.state_schema import SystemState


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
        """Simulates a weather API signal for the current city."""
        import random
        scenarios = [
            {"condition": "heavy_rain", "rainfall_mm": random.randint(35, 80), "temp_c": random.randint(28, 33),
             "wind_kmh": random.randint(30, 60), "alert": "Heavy Rain Advisory Active"},
            {"condition": "heatwave", "rainfall_mm": 0, "temp_c": random.randint(42, 47),
             "wind_kmh": random.randint(5, 15), "alert": "Extreme Heat Warning"},
            {"condition": "clear", "rainfall_mm": 0, "temp_c": random.randint(32, 38),
             "wind_kmh": random.randint(10, 20), "alert": "No active weather emergency"},
        ]
        scenario = random.choice(scenarios)
        scenario["city"] = city
        return scenario

    def _simulate_traffic_signal(self) -> Dict[str, Any]:
        """Simulates a traffic API signal."""
        import random
        congestion_level = random.choice(["normal", "moderate", "severe", "critical"])
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

        # ── Phase 1: Multi-source ingestion ──────────────────────────
        self._log(f"Phase 1 — Ingesting {len(social_posts)} social signal(s)...")
        for i, post in enumerate(social_posts, 1):
            self._log(f"  📡 Signal [{i}]: {post[:80]}{'...' if len(post)>80 else ''}")

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

        all_signals_text = " ".join(social_posts)
        crisis_type, base_confidence, matched_keywords = _detect_crisis_from_signal(all_signals_text)

        # Boost confidence from corroborating weather/traffic signals
        weather_boost = 0
        if weather:
            if crisis_type == "flood" and weather.get("condition") == "heavy_rain":
                weather_boost = 20
                self._log("  🔗 Corroborating weather signal: Heavy rain confirms flood crisis → +20% confidence")
            elif crisis_type == "heatwave" and weather.get("temp_c", 0) >= 42:
                weather_boost = 25
                self._log(f"  🔗 Corroborating weather signal: {weather['temp_c']}°C extreme temp confirms heatwave → +25% confidence")

        traffic_boost = 0
        if traffic:
            if traffic["congestion_level"] in ("severe", "critical") and crisis_type in ("flood", "accident"):
                traffic_boost = 15
                self._log(f"  🔗 Corroborating traffic signal: {traffic['congestion_level']} congestion confirms {crisis_type} impact → +15% confidence")

        final_confidence = min(base_confidence + weather_boost + traffic_boost, 99)

        if crisis_type is None:
            crisis_type = "accident"
            final_confidence = 45
            matched_keywords = ["unclassified signal"]
            self._log("  ⚠ No definitive crisis pattern detected — defaulting to unclassified emergency")
        else:
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
