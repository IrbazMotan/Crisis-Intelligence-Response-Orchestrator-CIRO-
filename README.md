# CIRO: Crisis Intelligence & Response Orchestrator 🌪️🚨

[![Hackathon: Challenge 3](https://img.shields.io/badge/Challenge_3-Crisis_Intelligence_%26_Response-blue?style=for-the-badge)](https://hackathon.example)
[![Powered by Google Antigravity](https://img.shields.io/badge/Powered_by-Google_Antigravity-orange?style=for-the-badge)](https://google.com)
[![Status: Autonomous](https://img.shields.io/badge/Status-Fully_Autonomous-success?style=for-the-badge)](https://google.com)

**CIRO** is an advanced, fully autonomous **Multi-Agent AI System** engineered to detect emerging crisis situations from raw, noisy, unstructured signals (like social media posts) and instantly orchestrate an intelligent emergency response.

Instead of relying on human operators to manually type in "Flood" or "Accident" and assign beds, **CIRO ingests raw text, autonomously parses the crisis severity, and triggers an intelligent dispatch pipeline.**

---

## 🌟 Why CIRO Wins Challenge 3

### 1. True Autonomous Signal Ingestion (No Hardcoding)
We abandoned static "mock buttons." CIRO features a **Raw Signal Ingestion Feed**. You can type *any* unstructured text in English, Urdu, or Roman Urdu (e.g., *"Massive flood near Aga Khan Hospital, cars are drowning"*). The Antigravity `TriageAgent` autonomously extracts the location using Nominatim API, detects the crisis type via NLP, and cross-references live weather/traffic telemetry to validate it.

### 2. Multi-Agent Reasoning & Confidence HUD
When a signal is ingested, the system doesn't just guess. It displays a live **Situation Analysis HUD**, detailing:
- **Confidence Level** (e.g., 92.5%) based on corroborating multi-source signals (weather, traffic, keywords).
- **Detected Severity** (e.g., CRITICAL).
- **AI Explanation** outlining *why* it made this decision.

### 3. Google Antigravity Orchestration
The system leverages a strict **Multi-Agent Pipeline**:
1. **`CrisisIntelligenceAgent`**: Fuses unstructured text, simulated live weather, and traffic data to detect the crisis and generate a coordinated action plan.
2. **`TriageAgent`**: Extracts coordinates, cross-validates fraud (e.g., checks Open-Meteo for actual rain if someone claims a flood), and assigns a triage severity.
3. **`HospitalFinderAgent`**: Executes a geographic ring-search to find the nearest hospital with required capacity (ICU/Ventilators).
4. **`SecurityAgent`**: Flags anomalous signals and blocks dispatch if validation fails.

---

## 🛠️ Architecture

### The Engine
CIRO runs on a powerful decoupled architecture:
- **Backend:** Python + FastAPI. Houses the `SystemState` schema and the Antigravity multi-agent loop.
- **Frontend:** React + Vite + Tailwind CSS. A high-performance, dark-mode, glassmorphic HUD designed for mission-critical command centers.
- **Telemetry Simulator:** A background thread that advances ambulances along OSRM-generated routing polylines, streaming updates via REST polling.

### The Decision Matrix
The frontend features a robust **Decision Matrix** tab. While the system operates autonomously, human operators can inspect the *exact reasoning trace* of the AI. It shows which hospitals were evaluated, rejected, and why (e.g., "Rejected: No ICU beds available").

---

## 🚀 Running the Project

### Prerequisites
- Node.js (v18+)
- Python (3.9+)

### 1. Start the Backend (Agent Engine)
```bash
cd ciro_platform/server
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Start the Frontend (Command Center)
```bash
cd ciro_platform/mobile-app
npm install
npm run dev
```

Open `http://localhost:5173` to view the Crisis Orchestration Dashboard.

---

## 💡 Demo Walkthrough

1. **Ingest a Signal:** Paste the provided Roman-Urdu mock signal for a Fire or type your own emergency dispatch text.
2. **Watch the HUD:** See the Antigravity agents parse the text, assign a confidence score, and explain their reasoning in real-time.
3. **Track the Telemetry:** Watch the map as the simulated ambulance navigates road networks to the patient, then to the hospital.
4. **Inspect the Matrix:** Open the "Decision Matrix" drawer to see the exact hospital inventory checks performed by the `HospitalFinderAgent`.

*Designed and engineered for the ultimate hackathon victory.* 🏆
