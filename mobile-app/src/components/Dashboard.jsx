import React, { useState, useEffect, useRef } from 'react';
import L from 'leaflet';
import { 
  ShieldAlert, 
  MapPin, 
  Truck, 
  Building2, 
  RotateCcw, 
  Activity, 
  CheckCircle2, 
  AlertTriangle,
  Send,
  ChevronUp,
  ChevronDown,
  Terminal,
  Compass,
  HeartPulse,
  Play
} from 'lucide-react';

const BACKEND_URL = `http://${window.location.hostname}:8000`;

// Static fallback hospital configurations
const HOSPITALS = [
  { id: "HOSP-A", name: "Hospital Alpha (Trauma Center)", hospital_type: "Trauma Center", coordinates: [24.8598, 67.0125] },
  { id: "HOSP-B", name: "Hospital Beta (General)", hospital_type: "General Hospital", coordinates: [24.9150, 67.0620] },
  { id: "HOSP-C", name: "Hospital Gamma (City Medical)", hospital_type: "Specialized Cardiac", coordinates: [24.9200, 67.0850] },
  { id: "HOSP-D", name: "Jinnah Hospital Complex", hospital_type: "Jinnah Hospital", coordinates: [24.8519, 67.0427] }
];

export default function Dashboard() {
  // Input settings
  const [triggerText, setTriggerText] = useState("Severe head-on collision near Gulshan, multiple casualties, needs ICU!");
  const [usePin, setUsePin] = useState(true);
  const [pinLat, setPinLat] = useState(24.9215);
  const [pinLng, setPinLng] = useState(67.0908);

  // Connection settings
  const [isApiMode, setIsApiMode] = useState(false);
  const [incidentId, setIncidentId] = useState("");
  const [loading, setLoading] = useState(false);
  
  // UI Display states
  const [isTerminalOpen, setIsTerminalOpen] = useState(true);
  const [isSOSOpen, setIsSOSOpen] = useState(true);
  const [incidentStage, setIncidentStage] = useState("idle"); // idle, triage, dispatched, hospital_found, admitted, warning
  
  // Telemetry updates
  const [currentAmbCoords, setCurrentAmbCoords] = useState(null);
  const [ambulanceRotation, setAmbulanceRotation] = useState(0);
  const [remainingDistance, setRemainingDistance] = useState(null);
  const [agentLogs, setAgentLogs] = useState([]);
  
  // Geographical overlays
  const [patientCoords, setPatientCoords] = useState(null);
  const [assignedHospital, setAssignedHospital] = useState(null);
  const [routePolyline, setRoutePolyline] = useState([]);
  const [currentTick, setCurrentTick] = useState(0);

  // Leaflet refs
  const mapRef = useRef(null);
  const ambulanceMarkerRef = useRef(null);
  const patientMarkerRef = useRef(null);
  const hospitalMarkerRef = useRef(null);
  const polylineRef = useRef(null);
  
  // Scrollers and interval hooks
  const terminalEndRef = useRef(null);
  const pollingIntervalRef = useRef(null);
  const prevAmbCoordsRef = useRef(null);

  // Auto scroll logs
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [agentLogs]);

  // Leaflet map viewport mount
  useEffect(() => {
    if (!mapRef.current) {
      const map = L.map('dashboard-map', {
        center: [24.8607, 67.0011],
        zoom: 12,
        zoomControl: false
      });

      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; CartoDB Dark Matter',
        maxZoom: 20
      }).addTo(map);

      mapRef.current = map;
    }

    // Plot hospital nodes
    HOSPITALS.forEach(hosp => {
      const customIcon = L.divIcon({
        className: 'custom-hosp-icon',
        html: `
          <div class="flex items-center justify-center w-8 h-8 rounded-lg bg-slate-900 border-2 border-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M12 7v10M7 12h10" />
            </svg>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });

      L.marker(hosp.coordinates, { icon: customIcon })
        .addTo(mapRef.current)
        .bindPopup(`<strong class="text-slate-900 font-bold">${hosp.name}</strong>`);
    });
  }, []);

  // Sync spatial assets on Leaflet markers
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;

    // Clear old layers
    if (patientMarkerRef.current) map.removeLayer(patientMarkerRef.current);
    if (hospitalMarkerRef.current) map.removeLayer(hospitalMarkerRef.current);
    if (ambulanceMarkerRef.current) map.removeLayer(ambulanceMarkerRef.current);
    if (polylineRef.current) map.removeLayer(polylineRef.current);

    // 1. Patient Beacon marker (Pulsing radar ring)
    if (patientCoords) {
      const pIcon = L.divIcon({
        className: 'patient-pulse-marker',
        html: `
          <div class="relative flex items-center justify-center w-8 h-8 rounded-full bg-red-950/80 border-2 border-red-500 shadow-[0_0_12px_rgba(239,68,68,0.8)]">
            <span class="absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-40 animate-ping"></span>
            <div class="w-3.5 h-3.5 rounded-full bg-red-500 border border-white"></div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });
      patientMarkerRef.current = L.marker(patientCoords, { icon: pIcon }).addTo(map);
    }

    // 2. Target hospital cross (Emerald glowing cross)
    if (assignedHospital) {
      const hIcon = L.divIcon({
        className: 'hospital-cross-marker',
        html: `
          <div class="flex items-center justify-center w-10 h-10 rounded-xl bg-emerald-950/85 border-2 border-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.9)]">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="3">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M12 7v10M7 12h10" />
            </svg>
          </div>
        `,
        iconSize: [40, 40],
        iconAnchor: [20, 20]
      });
      hospitalMarkerRef.current = L.marker(assignedHospital.coordinates, { icon: hIcon }).addTo(map);
    }

    // 3. Ambulance pointer (Linear GLIDE transition + vector rotation angle)
    if (currentAmbCoords) {
      const aIcon = L.divIcon({
        className: 'ambulance-bearing-marker',
        html: `
          <div class="flex items-center justify-center w-10 h-10 rounded-full bg-slate-900 border-2 border-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.8)] transition-all duration-1000 ease-linear" style="transform: rotate(${ambulanceRotation}deg);">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </div>
        `,
        iconSize: [40, 40],
        iconAnchor: [20, 20]
      });
      ambulanceMarkerRef.current = L.marker(currentAmbCoords, { icon: aIcon }).addTo(map);
    }

    // 4. Polyline route pathway
    if (routePolyline.length > 0) {
      polylineRef.current = L.polyline(routePolyline, {
        color: '#f59e0b',
        weight: 4,
        opacity: 0.8,
        dashArray: '8, 8',
        lineJoin: 'round'
      }).addTo(map);

      map.fitBounds(polylineRef.current.getBounds(), { padding: [40, 40] });
    } else if (patientCoords) {
      map.setView(patientCoords, 14);
    }

  }, [patientCoords, assignedHospital, currentAmbCoords, routePolyline, ambulanceRotation]);

  // Clean polling intervals on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, []);

  // Linear path waypoints generator
  const createLinearWaypoints = (start, mid, end) => {
    const waypoints = [];
    const steps = 6;
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      waypoints.push([
        parseFloat((start[0] + (mid[0] - start[0]) * t).toFixed(5)),
        parseFloat((start[1] + (mid[1] - start[1]) * t).toFixed(5))
      ]);
    }
    for (let i = 1; i <= steps; i++) {
      const t = i / steps;
      waypoints.push([
        parseFloat((mid[0] + (end[0] - mid[0]) * t).toFixed(5)),
        parseFloat((mid[1] + (end[1] - mid[1]) * t).toFixed(5))
      ]);
    }
    return waypoints;
  };

  // ─────────────────────────────────────────────
  // BACKEND API CONNECTORS & POLLING HOOKS
  // ─────────────────────────────────────────────

  // Trigger Intervention pipeline
  const triggerIntervention = async () => {
    if (!triggerText.trim() || loading) return;

    setLoading(true);
    setIncidentStage("triage");
    setAgentLogs([]);
    setCurrentTick(0);
    setRoutePolyline([]);
    setCurrentAmbCoords(null);
    prevAmbCoordsRef.current = null;
    setIsSOSOpen(false);

    const logEntry = (agent, msg) => {
      const time = new Date().toLocaleTimeString();
      setAgentLogs(prev => [...prev, { time, agent, msg }]);
    };

    logEntry("TriageAgent", "Initiating crisis trigger request to CIRO API portal...");

    try {
      // POST call to live FastAPI wrapper
      const response = await fetch(`${BACKEND_URL}/api/emergency/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: json.stringify({
          text: triggerText,
          latitude: usePin ? pinLat : null,
          longitude: usePin ? pinLng : null
        })
      });

      if (!response.ok) {
        throw new Error("FastAPI REST backend returned error response");
      }

      const data = await response.json();
      
      // Setup live API session
      setIsApiMode(true);
      setIncidentId(data.incident_id);
      logEntry("System", `Connected to active pipeline session: ${data.incident_id}`);

      // Handle occupied warning states instantly
      if (data.status === "warning") {
        setIncidentStage("warning");
        logEntry("HospitalFinderAgent", "[FAILED] Resource search failed. All hospitals fully occupied.");
        setLoading(false);
        return;
      }

      // Populate initial values
      const patientLoc = data.patient_details.location;
      setPatientCoords(patientLoc);
      
      // Start active 1000ms polling tracker
      startTelemetryPolling(data.incident_id);
      setLoading(false);

    } catch (error) {
      // Offline fallback sequence
      console.warn("FastAPI offline:", error);
      setIsApiMode(false);
      setIncidentStage("warning");
      setLoading(false);
      logEntry("System", "CRITICAL ERROR: Antigravity Multi-Agent Server (FastAPI) is offline. Cannot proceed with dispatch. Please ensure backend is running.");
    }
  };

  // Poll server-side telemetry status every 1000ms
  const startTelemetryPolling = (id) => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/emergency/status/${id}`);
        if (!res.ok) return;

        const data = await res.json();
        
        // 1. Sync event reasoning logs directly
        if (data.trace_logs) {
          const formattedLogs = data.trace_logs.map(log => ({
            time: log.timestamp,
            agent: log.agent,
            msg: log.message
          }));
          setAgentLogs(formattedLogs);
        }

        // 2. Sync incident stages
        if (data.patient_status === "dispatched") {
          setIncidentStage("dispatched");
        } else if (data.patient_status === "en_route") {
          setIncidentStage("hospital_found");
        } else if (data.patient_status === "admitted") {
          setIncidentStage("admitted");
          clearInterval(pollingIntervalRef.current); // Stop polling on admittal
        } else if (data.patient_status === "pending") {
          setIncidentStage("warning");
          clearInterval(pollingIntervalRef.current);
        }

        // 3. Sync hospital details
        if (data.hospital_telemetry) {
          setAssignedHospital({
            id: data.hospital_telemetry.hospital_id,
            name: data.hospital_telemetry.name,
            coordinates: data.hospital_telemetry.coordinates
          });
        }

        // 4. Sync ambulance GPS and route paths
        if (data.ambulance_telemetry) {
          const ambCoords = data.ambulance_telemetry.current_coordinates;
          const polyline = data.ambulance_telemetry.route_polyline;
          
          setRoutePolyline(polyline);

          // Calculate rotation angle (bearing) between coordinates
          if (prevAmbCoordsRef.current && ambCoords) {
            const lat1 = prevAmbCoordsRef.current[0], lng1 = prevAmbCoordsRef.current[1];
            const lat2 = ambCoords[0], lng2 = ambCoords[1];
            if (lat1 !== lat2 || lng1 !== lng2) {
              const angle = Math.atan2(lng2 - lng1, lat2 - lat1) * 180 / Math.PI;
              setAmbulanceRotation(Math.round(angle));
            }
          }
          
          prevAmbCoordsRef.current = ambCoords;
          setCurrentAmbCoords(ambCoords);
        }

        // Calculate custom distance remaining ratio
        if (data.ambulance_telemetry && data.hospital_telemetry) {
          const ambCoords = data.ambulance_telemetry.current_coordinates;
          const hospCoords = data.hospital_telemetry.coordinates;
          // Haversine ratio approximation
          const R = 6371.0;
          const lat1 = ambCoords[0] * Math.PI / 180;
          const lat2 = hospCoords[0] * Math.PI / 180;
          const dlat = (hospCoords[0] - ambCoords[0]) * Math.PI / 180;
          const dlon = (hospCoords[1] - ambCoords[1]) * Math.PI / 180;
          const a = Math.sin(dlat / 2) * Math.sin(dlat / 2) + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dlon / 2) * Math.sin(dlon / 2);
          const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
          setRemainingDistance(parseFloat((R * c).toFixed(2)));
        }

      } catch (err) {
        console.error("Error polling incident telemetry:", err);
      }
    }, 1000);
  };

  // Step tick trigger (Either calls backend /api/emergency/tick or offline mock logic)
  const stepSimulationTick = async () => {
    if (isApiMode) {
      try {
        const response = await fetch(`${BACKEND_URL}/api/emergency/tick`, { method: "POST" });
        if (response.ok) {
          const data = await response.json();
          // Tick triggered successfully. Polling will retrieve updated coordinate data!
          console.log("Tick executed successfully on server:", data);
        }
      } catch (error) {
        console.error("Failed executing API step tick:", error);
      }
    } else {
      // Local offline tick movement logic
      runLocalSimulatorTick();
    }
  };

  // LOCAL OFFLINE SIMULATORS REMOVED TO ENFORCE STRICT API USAGE

  // Reset complete telemetry workspace
  const resetSimulator = async () => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    
    setIncidentStage("idle");
    setPatientCoords(null);
    setAssignedHospital(null);
    setRoutePolyline([]);
    setCurrentAmbCoords(null);
    setCurrentTick(0);
    setRemainingDistance(null);
    setAgentLogs([]);
    setIsSOSOpen(true);
    setIncidentId("");

    if (isApiMode) {
      try {
        await fetch(`${BACKEND_URL}/api/emergency/reset`, { method: "POST" });
      } catch (err) {
        console.warn("Failed resetting FastAPI session state:", err);
      }
    }
  };

  return (
    <div className="max-w-md mx-auto h-[85vh] bg-slate-950 rounded-[45px] shadow-2xl border-[10px] border-slate-800 overflow-hidden relative font-sans flex flex-col select-none">
      
      {/* ─────────────────────────────────────────────────────────────
          1. STATUS HEADER STICKY BAR
          ───────────────────────────────────────────────────────────── */}
      <div className="sticky top-0 left-0 right-0 z-50 bg-slate-900/90 backdrop-blur-md border-b border-slate-800/80 px-6 pt-8 pb-3 flex flex-col gap-2">
        {/* Dynamic Island bezel header spacer */}
        <div className="w-24 h-4.5 bg-black rounded-full mx-auto mb-1 flex items-center justify-center">
          <span className="text-[7px] text-red-500 font-bold font-mono tracking-widest">CIRO AI</span>
        </div>

        {/* Dynamic Triage Pipeline Stages */}
        <div className="flex items-center justify-between text-[10px] font-bold tracking-wider">
          <div className="flex items-center gap-1.5">
            <HeartPulse className="w-4.5 h-4.5 text-red-500 animate-pulse" />
            <span className="font-orbitron text-slate-200">INTERVENTION LIFE STAGE</span>
          </div>
          <span className="font-mono text-slate-400">9:41 AM</span>
        </div>

        {/* Triage Stages Indicator */}
        <div className="grid grid-cols-5 gap-1 pt-1.5 text-[8px] font-bold text-center font-mono">
          {/* Stage 1: IDLE */}
          <div className={`p-1 rounded transition duration-200 ${
            incidentStage === 'idle' ? 'bg-slate-950 text-slate-200 border border-slate-800' : 'bg-slate-950/40 text-slate-600'
          }`}>
            ⚪ IDLE
          </div>
          {/* Stage 2: TRIAGE */}
          <div className={`p-1 rounded transition duration-200 ${
            incidentStage === 'triage' ? 'bg-amber-950 text-amber-300 border border-amber-500/30 animate-pulse' : 'bg-slate-950/40 text-slate-600'
          }`}>
            🟡 TRIAGE
          </div>
          {/* Stage 3: DISPATCHED */}
          <div className={`p-1 rounded transition duration-200 ${
            incidentStage === 'dispatched' ? 'bg-blue-950 text-blue-300 border border-blue-500/30 animate-pulse' : 'bg-slate-950/40 text-slate-600'
          }`}>
            🔵 DISPATCH
          </div>
          {/* Stage 4: HOSPITAL FOUND */}
          <div className={`p-1 rounded transition duration-200 ${
            incidentStage === 'hospital_found' ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/30 animate-pulse' : 'bg-slate-950/40 text-slate-600'
          }`}>
            🟢 ROUTED
          </div>
          {/* Stage 5: ADMITTED */}
          <div className={`p-1 rounded transition duration-200 ${
            incidentStage === 'admitted' ? 'bg-emerald-900 text-emerald-100 border border-emerald-400/40' : 'bg-slate-950/40 text-slate-600'
          }`}>
            ✅ ADMITTED
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          2. MAP CANVAS VIEWPORT
          ───────────────────────────────────────────────────────────── */}
      <div className="flex-1 relative bg-slate-950">
        <div id="dashboard-map" className="w-full h-full"></div>

        {/* Floating GPS telemetry block */}
        {remainingDistance !== null && (
          <div className="absolute top-4 left-4 z-40 bg-slate-950/90 border border-slate-800 rounded-xl p-2.5 shadow-lg flex items-center gap-2.5 font-mono text-[10px]">
            <div className="p-1.5 rounded-full bg-amber-500/20 text-amber-400">
              <Compass className="w-4 h-4 animate-spin" />
            </div>
            <div>
              <div className="text-slate-500 text-[8px] uppercase font-bold tracking-wider">Remaining distance</div>
              <div className="font-bold text-amber-400 text-xs">{remainingDistance} km</div>
            </div>
          </div>
        )}

        {/* Server connection indicator overlay */}
        <div className="absolute bottom-4 left-4 z-40 select-none bg-slate-950/80 px-2.5 py-1 rounded border border-slate-800 text-[8px] tracking-widest font-mono flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${isApiMode ? 'bg-emerald-500 animate-ping' : 'bg-amber-500 animate-pulse'}`}></span>
          <span className="text-slate-400 font-bold">{isApiMode ? 'API MODE: CONNECTED' : 'OFFLINE SIMULATOR'}</span>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          3. ANTIGRAVITY REASONING LOG TERMINAL (TOGGLEABLE)
          ───────────────────────────────────────────────────────────── */}
      <div className="absolute bottom-[300px] left-4 right-4 z-40 flex flex-col transition-all duration-300">
        <button
          onClick={() => setIsTerminalOpen(!isTerminalOpen)}
          className="self-end bg-slate-950/95 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-t-xl text-[10px] font-mono flex items-center gap-1.5 shadow-md active:scale-95"
        >
          <Terminal className="w-3.5 h-3.5 text-emerald-400" />
          <span>{isTerminalOpen ? "CLOSE AGENT TERMINAL" : "WATCH AGENT REASONINGS"}</span>
          {isTerminalOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
        </button>

        {isTerminalOpen && (
          <div className="h-32 bg-black/85 backdrop-blur-sm border border-slate-800 p-3 rounded-b-xl rounded-tl-xl font-mono text-[10px] text-emerald-400 overflow-y-auto flex flex-col gap-1.5 shadow-xl">
            {agentLogs.length === 0 ? (
              <div className="text-slate-600 italic text-center py-6">
                [SYSTEM IDLE] Awaiting trigger pipeline run...
              </div>
            ) : (
              <div className="space-y-1.5">
                {agentLogs.map((log, i) => (
                  <div key={i} className="border-l border-emerald-500/30 pl-2 py-0.5">
                    <span className="text-emerald-600 font-bold">[{log.time}] [{log.agent}]</span>{" "}
                    <span className="text-slate-300">{log.msg}</span>
                  </div>
                ))}
                <div ref={terminalEndRef} />
              </div>
            )}
          </div>
        )}
      </div>

      {/* ─────────────────────────────────────────────────────────────
          4. SOS FLOATING BOTTOM DRAWER SHEET
          ───────────────────────────────────────────────────────────── */}
      <div className={`bg-slate-950/95 backdrop-blur border-t border-slate-800 rounded-t-[32px] p-6 shadow-[0_-10px_25px_rgba(0,0,0,0.5)] z-40 transition-all duration-300 flex flex-col gap-4 ${
        isSOSOpen ? "h-[290px]" : "h-20"
      }`}>
        {/* Pull tab handle */}
        <div 
          onClick={() => setIsSOSOpen(!isSOSOpen)}
          className="w-12 h-1 bg-slate-800 rounded-full mx-auto select-none cursor-pointer flex items-center justify-center"
        >
        </div>

        {isSOSOpen ? (
          <div className="flex-1 flex flex-col justify-between">
            {/* Input area */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 tracking-wider">
                <span>DESCRIBE CRISIS SCENARIO</span>
                <span className="text-red-500 font-mono text-[8px] bg-red-950/50 px-1.5 py-0.5 rounded">HIGH URGENCY</span>
              </div>
              <textarea
                value={triggerText}
                onChange={(e) => setTriggerText(e.target.value)}
                placeholder="E.g., Severe head-on accident near Gulshan, patient has chest trauma..."
                className="w-full h-16 bg-slate-900 border border-slate-800/80 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-red-500 transition resize-none placeholder:text-slate-600"
              />
            </div>

            {/* Submit Intervention gradient button */}
            <button
              onClick={triggerIntervention}
              disabled={loading || !triggerText.trim()}
              className="w-full bg-gradient-to-r from-red-600 to-rose-500 hover:from-red-500 hover:to-rose-400 disabled:from-slate-800 disabled:to-slate-800 text-white font-orbitron font-extrabold text-xs py-3 px-4 rounded-xl shadow-lg active:scale-95 transition-all duration-150 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Activity className="w-4 h-4 animate-spin" />
                  <span>RESOLVING INCIDENT...</span>
                </>
              ) : (
                <>
                  <ShieldAlert className="w-4.5 h-4.5 animate-pulse" />
                  <span>TRIGGER EMERGENCY INTERVENTION</span>
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-between text-xs px-2">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-red-500 animate-pulse" />
              <div>
                <div className="font-bold text-slate-200">CIRO Mobile Dashboard</div>
                <div className="text-[9px] text-slate-500 uppercase tracking-wider">Active Pipeline Session</div>
              </div>
            </div>
            
            <div className="flex gap-2">
                onClick={resetSimulator}
                className="bg-slate-900 border border-slate-800 text-slate-400 px-3 py-1.5 rounded-lg text-[9px] font-bold font-mono transition duration-150 active:scale-95"
              >
                RESET
              </button>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
