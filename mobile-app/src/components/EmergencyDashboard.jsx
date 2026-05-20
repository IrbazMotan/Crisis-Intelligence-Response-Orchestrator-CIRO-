import React, { useState, useEffect, useRef } from 'react';
import L from 'leaflet';
import { 
  ShieldAlert, 
  MapPin, 
  Search, 
  Activity, 
  CheckCircle2, 
  AlertTriangle,
  Compass,
  Heart,
  Droplets,
  Sun,
  Flame,
  ChevronUp,
  ChevronDown,
  Terminal,
  Clock,
  ArrowRight,
  ShieldCheck,
  PartyPopper,
  Sparkles,
  Zap,
  Navigation,
  Send
} from 'lucide-react';

const BACKEND_URL = `http://${window.location.hostname}:8000`;



const getDistanceKm = (c1, c2) => {
  const R = 6371.0;
  const lat1 = c1[0] * Math.PI / 180;
  const lat2 = c2[0] * Math.PI / 180;
  const dlat = (c2[0] - c1[0]) * Math.PI / 180;
  const dlon = (c2[1] - c1[1]) * Math.PI / 180;
  const a = Math.sin(dlat / 2) * Math.sin(dlat / 2) + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dlon / 2) * Math.sin(dlon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return parseFloat((R * c).toFixed(2));
};

export default function EmergencyDashboard() {
  // Geolocation HUD States
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("info"); // info, success, warning, error

  // State Fields
  const [patientCoords, setPatientCoords] = useState({ lat: 24.8607, lng: 67.0011 }); // defaults to Karachi
  const [patientLocation, setPatientLocation] = useState("📍 Live GPS Coordinates Synchronized");
  const [isLocationManuallyEdited, setIsLocationManuallyEdited] = useState(false);
  const [rawSignalText, setRawSignalText] = useState("");
  const [patientConfidence, setPatientConfidence] = useState(0);
  const [patientExplanation, setPatientExplanation] = useState("");
  const [patientSeverity, setPatientSeverity] = useState("");

  // Pakistan Big Cities Selector HUD
  const [selectedCity, setSelectedCity] = useState("Karachi");
  const [cityTemp, setCityTemp] = useState(null);

  const fetchCityWeather = async (cityObj) => {
    try {
      const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${cityObj.coords.lat}&longitude=${cityObj.coords.lng}&current=temperature_2m`);
      if (res.ok) {
        const data = await res.json();
        setCityTemp(Math.round(data.current?.temperature_2m || 33.2));
      }
    } catch (err) {
      console.warn("Failed fetching city weather:", err);
    }
  };

  useEffect(() => {
    if (selectedCity === "Live GPS") return;
    // Removed hardcoded city switching logic
  }, [selectedCity]);

  // ─────────────────────────────────────────────
  // STATE CONTROL MACHINE (Three Steps)
  // ─────────────────────────────────────────────
  const [appStep, setAppStep] = useState(1); // Step 1: Intake Form, Step 2: Intermediate Triage loading, Step 3: Active Map Tracking

  // Operational states
  const [isApiMode, setIsApiMode] = useState(false);
  const [incidentId, setIncidentId] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentStatus, setCurrentStatus] = useState("idle"); 
  const [agentLogs, setAgentLogs] = useState([]);
  const [ambulancePosition, setAmbulancePosition] = useState(null); // { lat, lng }
  
  const [ambulanceRotation, setAmbulanceRotation] = useState(0);
  const [remainingDistance, setRemainingDistance] = useState(null);
  const [assignedHospital, setAssignedHospital] = useState(null);
  const [routePolyline, setRoutePolyline] = useState([]);
  const [currentTick, setCurrentTick] = useState(0);
  const [showCelebrationModal, setShowCelebrationModal] = useState(false);
  const [backendWarning, setBackendWarning] = useState("");
  const [consoleTab, setConsoleTab] = useState("logs"); // "logs" or "matchmaker"

  // Leaflet refs
  const mapRef = useRef(null);
  const ambulanceMarkerRef = useRef(null);
  const patientMarkerRef = useRef(null);
  const hospitalMarkerRef = useRef(null);
  const polylineRef = useRef(null);

  const terminalEndRef = useRef(null);
  const pollingIntervalRef = useRef(null);
  const prevAmbCoordsRef = useRef(null);

  // Auto scroll logs
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [agentLogs]);

  // Request location on mount
  useEffect(() => {
    fetchGeolocation();
  }, []);

  // Geolocation access hook
  const fetchGeolocation = () => {
    setToastType("info");
    setToastMessage("📍 Synchronizing live GPS coordinates...");

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const latVal = position.coords.latitude;
          const lngVal = position.coords.longitude;
          
          setPatientCoords({ lat: latVal, lng: lngVal });
          setSelectedCity("Live GPS");
          setIsLocationManuallyEdited(false);
          
          // 2. Reverse Geocode to get a real readable address
          try {
            const nomRes = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${latVal}&lon=${lngVal}&format=json`);
            if (nomRes.ok) {
              const data = await nomRes.json();
              if (data && data.display_name) {
                // Keep it concise, take first 3 parts of the address
                const shortAddress = data.display_name.split(",").slice(0, 3).join(",");
                setPatientLocation(shortAddress);
              } else {
                setPatientLocation(`GPS Location: ${latVal.toFixed(4)}, ${lngVal.toFixed(4)}`);
              }
            }
          } catch (err) {
            setPatientLocation(`GPS Location: ${latVal.toFixed(4)}, ${lngVal.toFixed(4)}`);
          }

          setToastType("success");
          setToastMessage("✅ Location Synchronized");
        },
        (error) => {
          console.warn("Geolocation permission denied.", error);
          setToastType("warning");
          setToastMessage("⚠️ GPS unavailable. Please enter address manually.");
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    } else {
      setToastType("error");
      setToastMessage("⚠️ Browser Geolocation modules unsupported.");
    }
  };

  // Leaflet map viewport mount (triggers when Step 3 reveals)
  useEffect(() => {
    if (appStep === 3 && !mapRef.current) {
      setTimeout(() => {
        const map = L.map('tracking-map', {
          center: [patientCoords.lat, patientCoords.lng],
          zoom: 13,
          zoomControl: false
        });

        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
          attribution: '&copy; CartoDB Dark Matter',
          maxZoom: 20
        }).addTo(map);

        mapRef.current = map;

      }, 100);
    }
  }, [appStep, selectedCity]);

  // Sync spatial markers to active map instance
  useEffect(() => {
    if (!mapRef.current || appStep !== 3) return;
    const map = mapRef.current;

    // Remove old layers
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
      patientMarkerRef.current = L.marker([patientCoords.lat, patientCoords.lng], { icon: pIcon })
        .addTo(map)
        .bindTooltip(`<div class="text-[8px] tracking-widest text-red-400 font-bold uppercase">${patientLocation || "PATIENT LOCATION"}</div>`, {
          permanent: true,
          direction: 'top',
          offset: [0, -16],
          className: 'custom-patient-tooltip'
        });
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
      hospitalMarkerRef.current = L.marker(assignedHospital.coordinates, { icon: hIcon })
        .addTo(map)
        .bindTooltip(`<div class="text-[8px] tracking-widest text-emerald-400 font-bold uppercase">${assignedHospital.name}</div>`, {
          permanent: true,
          direction: 'top',
          offset: [0, -22],
          className: 'custom-map-tooltip'
        });
    }

    // 3. Ambulance pointer (Linear GLIDE transition + vector rotation angle)
    if (ambulancePosition) {
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
      ambulanceMarkerRef.current = L.marker([ambulancePosition.lat, ambulancePosition.lng], { icon: aIcon }).addTo(map);
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
      map.setView([patientCoords.lat, patientCoords.lng], 14);
    }
  }, [patientCoords, assignedHospital, ambulancePosition, routePolyline, ambulanceRotation, appStep]);

  // ─────────────────────────────────────────────
  // REAL ROAD ROUTING ENGINE (OSRM Shortest Path)
  // Uses OpenStreetMap routing to find actual road geometry
  // Falls back to L-shaped simulation if OSRM is offline
  // ─────────────────────────────────────────────
  const fetchOSRMRoute = async (startCoords, endCoords) => {
    try {
      const url = `https://router.project-osrm.org/route/v1/driving/${startCoords[1]},${startCoords[0]};${endCoords[1]},${endCoords[0]}?overview=full&geometries=geojson&steps=false&alternatives=false`;
      const res = await fetch(url, { signal: AbortSignal.timeout(6000) });
      if (!res.ok) throw new Error("OSRM offline");
      const data = await res.json();
      if (data.code !== "Ok" || !data.routes?.length) throw new Error("No route found");
      const coords = data.routes[0].geometry.coordinates;
      const durationSec = data.routes[0].duration;
      const distanceM = data.routes[0].distance;
      const waypoints = coords.map(c => [parseFloat(c[1].toFixed(5)), parseFloat(c[0].toFixed(5))]);
      return { waypoints, durationMin: Math.round(durationSec / 60), distanceKm: parseFloat((distanceM / 1000).toFixed(2)), routeSource: "OSRM" };
    } catch (err) {
      console.warn("OSRM unavailable, falling back to simulation:", err);
      return buildSimulationRoute(startCoords, endCoords);
    }
  };

  // L-shaped 2-phase fallback route (mimics real road turns)
  const buildSimulationRoute = (start, end) => {
    const waypoints = [];
    for (let i = 0; i <= 7; i++) {
      const t = i / 7;
      waypoints.push([parseFloat((start[0] + (end[0] - start[0]) * t).toFixed(5)), parseFloat((start[1]).toFixed(5))]);
    }
    for (let i = 1; i <= 7; i++) {
      const t = i / 7;
      waypoints.push([parseFloat((end[0]).toFixed(5)), parseFloat((start[1] + (end[1] - start[1]) * t).toFixed(5))]);
    }
    const distKm = getDistanceKm(start, end);
    return { waypoints, durationMin: Math.round((distKm / 40) * 60), distanceKm: parseFloat((distKm * 1.15).toFixed(2)), routeSource: "SIM" };
  };

  // ─────────────────────────────────────────────
  // SUBMIT TRIGGER DISPATCHER
  // ─────────────────────────────────────────────
  const launchAgentDispatch = async () => {
    if (!rawSignalText.trim()) {
      setToastType("error");
      setToastMessage("⚠️ Please enter a raw emergency signal.");
      return;
    }

    setLoading(true);
    setCurrentStatus("triage");
    setAgentLogs([]);
    setCurrentTick(0);
    setRoutePolyline([]);
    setAmbulancePosition(null);
    prevAmbCoordsRef.current = null;
    setShowCelebrationModal(false);
    setBackendWarning("");
    
    // Switch immediately to Intermediate loading Step 2
    setAppStep(2);

    const logEntry = (agent, msg) => {
      const time = new Date().toLocaleTimeString();
      setAgentLogs(prev => [...prev, `[${time}] [${agent}] ${msg}`]);
    };

    logEntry("TriageAgent", `Initiating Autonomous Signal Ingestion: Parsing raw string...`);
    logEntry("TriageAgent", `Ingested Signal: "${rawSignalText}"`);

    let targetLat = patientCoords.lat;
    let targetLng = patientCoords.lng;
    
    logEntry("TriageAgent", `[GPS SYNC] Attaching active browser GPS coordinates: (${targetLat.toFixed(4)}, ${targetLng.toFixed(4)})`);

    try {
      const payload = {
        text: rawSignalText,
        latitude: targetLat,
        longitude: targetLng
      };

      const response = await fetch(`${BACKEND_URL}/api/emergency/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error("REST API offline");

      const data = await response.json();
      setIsApiMode(true);
      setIncidentId(data.incident_id);
      logEntry("System", `Exposed pipeline incident id: ${data.incident_id}`);

      if (data.status === "warning") {
        setCurrentStatus("warning");
        setBackendWarning(data.warning || data.message);
        logEntry("HospitalFinderAgent", "[FAILED] Fallback rejections warning. Registries exhausted.");
        setLoading(false);
        setAppStep(3); // transition to view warnings in Step 3
        return;
      }

      if (data.status === "rejected" || data.patient_status === "rejected") {
        setCurrentStatus("warning");
        setBackendWarning(data.warning || data.message);
        logEntry("SecurityAgent", `[REJECTED] ${data.message || "Emergency validation blocked by security protocol."}`);
        setLoading(false);
        setAppStep(3);
        return;
      }

      // Automatically transition to Step 3 after a 3-second cinematic mock interval
      setTimeout(() => {
        setAppStep(3);
        startTelemetryPolling(data.incident_id);
      }, 3000);
      
      setLoading(false);

    } catch (err) {
      console.warn("FastAPI offline:", err);
      setToastType("error");
      setToastMessage("⚠️ Backend Server Offline. Ensure uvicorn main:app is running.");
      setCurrentStatus("warning");
      setLoading(false);
      setIsApiMode(false);
      logEntry("System", "CRITICAL ERROR: Antigravity Multi-Agent Server (FastAPI) is offline. Cannot proceed with dispatch.");
    }
  };

  const startTelemetryPolling = (id) => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/emergency/status/${id}`);
        if (!res.ok) return;

        const data = await res.json();
        
        if (data.trace_logs) {
          const formattedLogs = data.trace_logs.map(log => 
            `[${log.timestamp}] [${log.agent}] ${log.message}`
          );
          setAgentLogs(formattedLogs);
        }

        if (data.patient_status === "dispatched") {
          setCurrentStatus("dispatched");
        } else if (data.patient_status === "en_route") {
          setCurrentStatus("hospital_found");
        } else if (data.patient_status === "admitted") {
          setCurrentStatus("admitted");
          setShowCelebrationModal(true); 
          clearInterval(pollingIntervalRef.current);
        } else if (data.patient_status === "pending") {
          setCurrentStatus("warning");
          setBackendWarning(data.warning || data.message);
          clearInterval(pollingIntervalRef.current);
        } else if (data.patient_status === "rejected") {
          setCurrentStatus("warning");
          setBackendWarning(data.warning || data.message);
          clearInterval(pollingIntervalRef.current);
        }

        if (data.patient_confidence !== undefined) {
          setPatientConfidence(data.patient_confidence);
        }
        if (data.patient_explanation) {
          setPatientExplanation(data.patient_explanation);
        }
        if (data.patient_severity) {
          setPatientSeverity(data.patient_severity);
        }

        if (data.hospital_telemetry) {
          setAssignedHospital({
            id: data.hospital_telemetry.hospital_id,
            name: data.hospital_telemetry.name,
            coordinates: data.hospital_telemetry.coordinates
          });
        }

        if (data.ambulance_telemetry) {
          const ambCoords = data.ambulance_telemetry.current_coordinates;
          const polyline = data.ambulance_telemetry.route_polyline;
          setRoutePolyline(polyline);

          if (prevAmbCoordsRef.current && ambCoords) {
            const lat1 = prevAmbCoordsRef.current[0], lng1 = prevAmbCoordsRef.current[1];
            const lat2 = ambCoords[0], lng2 = ambCoords[1];
            if (lat1 !== lat2 || lng1 !== lng2) {
              const angle = Math.atan2(lng2 - lng1, lat2 - lat1) * 180 / Math.PI;
              setAmbulanceRotation(Math.round(angle));
            }
          }
          prevAmbCoordsRef.current = ambCoords;
          setAmbulancePosition({ lat: ambCoords[0], lng: ambCoords[1] });
        }

        if (data.ambulance_telemetry && data.hospital_telemetry) {
          const ambCoords = data.ambulance_telemetry.current_coordinates;
          const hospCoords = data.hospital_telemetry.coordinates;
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
        console.error("Polling error:", err);
      }
    }, 1000);
  };

  const stepSimulationTick = async () => {
    if (isApiMode) {
      try {
        await fetch(`${BACKEND_URL}/api/emergency/tick`, { method: "POST" });
      } catch (err) {
        console.error("Step tick failed:", err);
      }
    } else {
      runLocalSimulatorTick();
    }
  };

  // Offline simulator removed to enforce strict Agentic Backend Usage

  // Offline simulator logic removed

  const triggerArrivePatient = async () => {
    if (isApiMode) {
      try {
        await fetch(`${BACKEND_URL}/api/emergency/arrive_patient`, { method: "POST" });
      } catch (err) {
        console.error("Arrive patient failed:", err);
      }
    } else {
      if (routePolyline.length > 0) {
        const midIdx = Math.min(5, routePolyline.length - 1);
        setCurrentTick(midIdx);
        const curr = routePolyline[midIdx];
        setAmbulancePosition({ lat: curr[0], lng: curr[1] });
        setCurrentStatus("hospital_found");
        const time = new Date().toLocaleTimeString();
        setAgentLogs(prev => [
          ...prev,
          `[${time}] [Telemetry] ⚡ ARRIVED AT PATIENT (Boarded successfully).`
        ]);
      }
    }
  };

  const triggerArriveHospital = async () => {
    if (isApiMode) {
      try {
        await fetch(`${BACKEND_URL}/api/emergency/arrive_hospital`, { method: "POST" });
      } catch (err) {
        console.error("Arrive hospital failed:", err);
      }
    } else {
      if (routePolyline.length > 0) {
        const endIdx = routePolyline.length - 1;
        setCurrentTick(endIdx);
        const curr = routePolyline[endIdx];
        setAmbulancePosition({ lat: curr[0], lng: curr[1] });
        setRemainingDistance(0);
        setCurrentStatus("admitted");
        setShowCelebrationModal(true);
        const time = new Date().toLocaleTimeString();
        setAgentLogs(prev => [
          ...prev,
          `[${time}] [Telemetry] ⚡ ARRIVED AT HOSPITAL. Admitted successfully.`
        ]);
      }
    }
  };

  // Automatic Simulation Ticking every 3 seconds (Bykea / Indrive style)
  useEffect(() => {
    if (appStep !== 3 || currentStatus === "admitted" || currentStatus === "warning") return;

    const interval = setInterval(() => {
      if (isApiMode) {
        stepSimulationTick();
      } else {
        runLocalSimulatorTick();
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [appStep, currentStatus, routePolyline, currentTick, isApiMode]);

  const resetAll = async () => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    
    setAppStep(1);
    setCurrentStatus("idle");
    setAssignedHospital(null);
    setRoutePolyline([]);
    setAmbulancePosition(null);
    setCurrentTick(0);
    setRemainingDistance(null);
    setAgentLogs([]);
    setIncidentId("");
    setShowCelebrationModal(false);

    if (isApiMode) {
      try {
        await fetch(`${BACKEND_URL}/api/emergency/reset`, { method: "POST" });
      } catch (err) {
        console.warn("Failed resetting FastAPI:", err);
      }
    }
  };

  // Parse logs for visual hospital finder HUD
  const parseHospitalSelection = () => {
    const evaluations = [];
    let currentEval = null;

    agentLogs.forEach(log => {
      // 1. Detect checking start: Check #1: Aga Khan University Hospital (AKUH) (HOSP-B) ---
      if (log.includes("--- Ring") && log.includes("Check #")) {
        const ringMatch = log.match(/Ring\s+(\d+)km/);
        const nameIdMatch = log.match(/Check\s+#\d+:\s*(.*?)\s*\((.*?)\)\s*---/);
        
        const ring = ringMatch ? ringMatch[1] : "";
        const name = nameIdMatch ? nameIdMatch[1] : "Hospital Candidate";
        const id = nameIdMatch ? nameIdMatch[2] : "UNKNOWN";
        
        currentEval = { 
          id, 
          name, 
          ring,
          beds: "-", 
          icu: "-", 
          vents: "-", 
          status: "Checking", 
          reason: "Agent contacting facility management...",
          eta: "-",
          distance: "-"
        };
        
        // Find distance/eta in preceding logs if available
        // e.g. "  #1 Aga Khan University Hospital (AKUH) - 6.18 km | ETA: 10 min"
        for (let i = agentLogs.length - 1; i >= 0; i--) {
          const l = agentLogs[i];
          if (l.includes(name) && l.includes("km | ETA:")) {
            const distMatch = l.match(/-\s*([\d\.]+)\s*km/);
            const etaMatch = l.match(/ETA:\s*(\d+)\s*min/);
            if (distMatch) currentEval.distance = distMatch[1];
            if (etaMatch) currentEval.eta = etaMatch[1];
            break;
          }
        }

        evaluations.push(currentEval);
      }

      // 2. Parse inventory response: "Response  -> Beds: 15 | ICU: 8 | Ventilators: 4"
      if (log.includes("Response  -> Beds:") && currentEval) {
        const bedsMatch = log.match(/Beds:\s*(\d+)/);
        const icuMatch = log.match(/ICU:\s*(\d+)/);
        const ventMatch = log.match(/Ventilators:\s*(\d+)/);
        if (bedsMatch) currentEval.beds = bedsMatch[1];
        if (icuMatch) currentEval.icu = icuMatch[1];
        if (ventMatch) currentEval.vents = ventMatch[1];
      }

      // 3. Parse fit check: "Fit Check -> ACCEPTED - ICU bed available"
      if (log.includes("Fit Check ->") && currentEval) {
        const reasonText = log.split("Fit Check ->")[1].trim();
        currentEval.reason = reasonText;
        if (reasonText.includes("ACCEPTED")) {
          currentEval.status = "Selected";
        } else {
          currentEval.status = "Rejected";
          // Simplify reasons for extreme readability
          if (reasonText.includes("Lacks specialized ICU ventilators")) {
            currentEval.reason = "Rejected: Lacks Ventilators";
          } else if (reasonText.includes("Lacks available ICU beds")) {
            currentEval.reason = "Rejected: Lacks ICU Beds";
          } else if (reasonText.includes("refuses admission (0 general beds)")) {
            currentEval.reason = "Rejected: General Beds Exhausted";
          } else if (reasonText.includes("road is blocked or heavily congested")) {
            currentEval.reason = "Rejected: Road Blocked / Congestion";
          }
        }
      }
    });

    return evaluations;
  };

  const hospitalMatches = parseHospitalSelection();

  return (
    <div className="w-full md:max-w-md min-h-[82vh] md:h-[86vh] flex flex-col bg-slate-950 p-5 text-white md:rounded-[40px] md:shadow-2xl md:border-8 md:border-slate-800 relative font-sans select-none overflow-y-auto transition-all duration-300">
      
      {/* ─────────────────────────────────────────────────────────────
          CELEBRATION SUCCESS MODAL BANNER
          ───────────────────────────────────────────────────────────── */}
      {showCelebrationModal && (
        <div className="absolute inset-0 bg-slate-950/85 backdrop-blur-md z-[100] flex items-center justify-center p-6 animate-fade-in">
          <div className="w-full bg-slate-900 border-2 border-emerald-500 rounded-[32px] p-6 shadow-[0_0_30px_rgba(16,185,129,0.3)] flex flex-col items-center text-center gap-4 relative overflow-hidden select-none">
            
            <div className="absolute -top-12 w-32 h-32 rounded-full bg-emerald-500/10 blur-xl pointer-events-none"></div>

            <div className="p-4 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 animate-bounce">
              <PartyPopper className="w-10 h-10" />
            </div>

            <div>
              <div className="text-[10px] font-mono tracking-widest text-emerald-400 font-extrabold uppercase mb-1">
                AUTONOMOUS MISSION ACCOMPLISHED
              </div>
              <h2 className="text-xl font-orbitron font-extrabold text-slate-100">
                PATIENT ADMITTED!
              </h2>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed font-sans max-w-[240px]">
              The Google Antigravity autonomous rescue pipeline completed successfully. Patient has been cleared at <span className="text-emerald-400 font-bold">{assignedHospital?.name}</span>.
            </p>

            {/* Simulated Outcome Metrics */}
            <div className="w-full bg-slate-950/60 border border-slate-800 rounded-xl p-3 flex flex-col gap-2 mt-2">
               <div className="text-[9px] font-mono tracking-widest text-slate-500 uppercase font-bold text-left">AGENTIC SIMULATED OUTCOMES</div>
               <div className="flex justify-between items-center text-xs">
                 <span className="text-slate-400">Threat Detection</span>
                 <span className="text-emerald-400 font-mono font-bold">{(patientConfidence * 100).toFixed(1)}% Confidence</span>
               </div>
               <div className="flex justify-between items-center text-xs">
                 <span className="text-slate-400">Severity Handled</span>
                 <span className="text-emerald-400 font-mono font-bold">{patientSeverity ? patientSeverity.toUpperCase() : "CRITICAL"}</span>
               </div>
               <div className="flex justify-between items-center text-xs">
                 <span className="text-slate-400">Resource Match</span>
                 <span className="text-emerald-400 font-mono font-bold">100% (Confirmed)</span>
               </div>
            </div>

            <button
              onClick={resetAll}
              className="w-full bg-gradient-to-r from-emerald-600 to-teal-500 text-white font-orbitron font-extrabold text-xs py-3.5 px-4 rounded-xl shadow-lg shadow-emerald-950/65 hover:brightness-110 active:scale-[0.97] transition duration-150 flex items-center justify-center gap-1.5"
            >
              <Sparkles className="w-4 h-4" />
              <span>RESET WORKSPACE</span>
            </button>
          </div>
        </div>
      )}

      {/* Dynamic Island notch decor (only on larger mock-frame viewports) */}
      <div className="hidden md:flex absolute top-0 left-1/2 -translate-x-1/2 w-32 h-5 bg-black rounded-b-xl z-50 items-center justify-center">
        <div className="w-2.5 h-2.5 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center mr-1">
          <div className="w-1 h-1 rounded-full bg-blue-600"></div>
        </div>
        <div className="w-6 h-1 bg-slate-950 rounded-full"></div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          SCREEN 1: THE INTAKE FORM (appStep === 1)
          ───────────────────────────────────────────────────────────── */}
      {appStep === 1 && (
        <div className="flex-1 flex flex-col space-y-4 pt-2 md:pt-4">
          
          <h2 className="text-xl font-extrabold font-orbitron tracking-tight text-white mb-2">
            Crisis Orchestration
          </h2>

          {/* Alert Ribbon if GPS issues */}
          {toastType === "warning" && (
            <div className="w-full bg-amber-500/10 border border-amber-500/30 rounded-xl p-3.5 text-xs text-amber-400 flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 shrink-0 text-amber-500 animate-bounce" />
              <span className="leading-snug">⚠️ GPS unavailable. Please enter address manually below.</span>
            </div>
          )}

          {/* Unstructured Signal Feed */}
          <div className="flex-1 flex flex-col space-y-3 mb-2">
            <label className="text-[10px] font-mono tracking-wider font-bold text-slate-400 uppercase">RAW SIGNAL INGESTION</label>
            <div className="relative flex-1 min-h-[140px]">
              <textarea
                value={rawSignalText}
                onChange={(e) => setRawSignalText(e.target.value)}
                placeholder="Type or paste any raw emergency signal here (English, Urdu, or Roman Urdu). The Agentic AI will autonomously parse the crisis type, extract coordinates, and determine severity..."
                className="w-full h-full bg-slate-900 border border-slate-800 rounded-xl p-4 text-xs font-semibold focus:border-red-500 transition-all text-white placeholder-slate-600 outline-none focus:outline-none resize-none leading-relaxed"
              />
            </div>
            
            {/* Quick Mock Chips for Demo Speed */}
            <div className="space-y-1.5">
              <label className="text-[8px] font-mono tracking-wider text-slate-500 uppercase">QUICK INJECT MOCK DATA:</label>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setRawSignalText("Massive flood near Aga Khan Hospital stadium road, cars are drowning, we need boats!")}
                  className="px-2.5 py-1.5 bg-blue-500/10 border border-blue-500/30 rounded-lg text-[9px] text-blue-300 hover:bg-blue-500/20 transition-colors"
                >
                  🌊 Flood (Seelab)
                </button>
                <button
                  onClick={() => setRawSignalText("Clifton block 5 mein aag lag gayi hai, building se dhuaan nikal raha hai, severe burning, please dispatch firetruck.")}
                  className="px-2.5 py-1.5 bg-red-500/10 border border-red-500/30 rounded-lg text-[9px] text-red-300 hover:bg-red-500/20 transition-colors"
                >
                  🔥 Fire (Aagh)
                </button>
                <button
                  onClick={() => setRawSignalText("Terrible multi-car accident on Shahrah-e-Faisal near FTC building. Need ICU and critical trauma support immediately.")}
                  className="px-2.5 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded-lg text-[9px] text-amber-300 hover:bg-amber-500/20 transition-colors"
                >
                  🚗 Accident (Hadsa)
                </button>
              </div>
            </div>
          </div>

          {/* Submission trigger dispatcher */}
          <div className="flex-1 flex flex-col justify-end pt-4">
            <button
              onClick={launchAgentDispatch}
              disabled={loading}
              className="w-full bg-gradient-to-r from-red-600 to-rose-500 text-white font-bold py-4 rounded-xl tracking-wide shadow-xl active:scale-[0.97] transition-all text-sm"
            >
              {loading ? "DISPATCHING AGENTS..." : "LAUNCH AUTONOMOUS DISPATCH"}
            </button>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SCREEN 2: INTERMEDIATE REASONING TRACE (appStep === 2)
          ───────────────────────────────────────────────────────────── */}
      {appStep === 2 && (
        <div className="flex-1 flex flex-col justify-center items-center py-12 px-4 space-y-8 select-none">
          
          <div className="w-20 h-20 rounded-full bg-red-500/20 animate-ping flex items-center justify-center text-red-500 mx-auto my-12">
            <ShieldAlert className="w-7 h-7 animate-pulse" />
          </div>

          <div className="text-center space-y-2">
            <h2 className="text-[10px] font-mono tracking-widest text-emerald-400 font-extrabold uppercase">
              SITUATION ANALYSIS HUD
            </h2>
            <h1 className="text-base font-orbitron font-extrabold text-slate-100">
              ORCHESTRATING MISSION...
            </h1>
          </div>

          {/* AI Situation Analysis HUD */}
          <div className="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-4 flex flex-col gap-3">
            <div className="flex justify-between items-center border-b border-slate-800 pb-2">
              <span className="text-[9px] font-mono text-slate-500 font-bold uppercase">Confidence Score</span>
              <span className="text-emerald-400 font-mono font-bold text-sm">{(patientConfidence * 100).toFixed(1)}%</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[9px] font-mono text-slate-500 font-bold uppercase">Detected Severity</span>
              <span className={`text-xs font-bold ${patientSeverity === 'critical' ? 'text-red-500' : 'text-amber-500'}`}>
                {patientSeverity ? patientSeverity.toUpperCase() : "ANALYZING..."}
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[9px] font-mono text-slate-500 font-bold uppercase">AI Explanation</span>
              <span className="text-xs text-slate-300 leading-relaxed italic">
                {patientExplanation || "Awaiting Antigravity Triage Agent reasoning trace..."}
              </span>
            </div>
          </div>

          {/* Streaming terminal parser logs */}
          <div className="w-full font-mono text-[10px] text-emerald-400 bg-black/60 p-3 rounded-xl border border-slate-800/80 h-28 overflow-y-auto flex flex-col gap-1.5 text-left">
            <div className="flex items-center gap-1.5 border-b border-slate-900 pb-1.5 mb-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
              <span className="text-[8px] font-bold text-slate-500">ANTIGRAVITY PIPELINE TRACE</span>
            </div>
            <div className="animate-pulse space-y-1">
              {agentLogs.length > 0 ? (
                agentLogs.slice(-4).map((log, i) => <div key={i}>{log}</div>)
              ) : (
                <>
                  <div>[TriageAgent] Ingesting unstructured signal parameters...</div>
                  <div>[TriageAgent] Extracting locations and applying NLP...</div>
                  <div className="text-slate-500">[HospitalFinderAgent] Analyzing crisis parameters...</div>
                </>
              )}
            </div>
          </div>

        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          SCREEN 3: RIDE-HAILING TRACKING CANVAS (appStep === 3)
          ───────────────────────────────────────────────────────────── */}
      {appStep === 3 && (
        <div className="flex-1 flex flex-col relative h-full transition-all duration-300">
          
          {/* Live Status overlay Card */}
          <div className="absolute top-4 left-4 right-4 bg-slate-900/95 backdrop-blur-md border border-slate-800 rounded-2xl p-4 shadow-2xl z-50 flex items-center justify-between select-none">
            {currentStatus === "warning" ? (
              <div className="w-full text-center py-1">
                <div className="text-[8px] font-mono tracking-widest text-red-500 font-extrabold uppercase flex items-center justify-center gap-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-red-500 animate-pulse" />
                  <span>CRITICAL DISPATCH ABORTED</span>
                </div>
                <h2 className="text-[10px] font-extrabold text-slate-200 mt-1.5 leading-snug">
                  {backendWarning || `False Emergency Blocked. Live Temperature of ${cityTemp !== null ? `${cityTemp}°C` : "33.2°C"} in ${selectedCity} is below threshold.`}
                </h2>
              </div>
            ) : (
              <>
                <div>
                  <div className="text-[7px] text-slate-500 uppercase tracking-widest font-extrabold">Dispatch Status</div>
                  <h2 className="text-[10px] font-bold text-slate-300 mt-0.5">🚨 Ambulance Dispatched</h2>
                  <div className="text-xs font-orbitron font-extrabold text-teal-400 animate-pulse mt-0.5">
                    Arriving in 5 mins
                  </div>
                </div>
                <div className="text-right pl-2">
                  <div className="text-[7px] text-slate-500 uppercase tracking-widest font-extrabold">Destination Node</div>
                  <div className="text-[10px] font-bold text-slate-200 mt-0.5 leading-snug">
                    {assignedHospital ? assignedHospital.name : "Jinnah Medical Center"}
                  </div>
                  {assignedHospital && assignedHospital.hospital_type && (
                    <span className="inline-block mt-1 px-1.5 py-0.5 text-[7px] font-mono font-bold tracking-wider rounded uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      {assignedHospital.hospital_type}
                    </span>
                  )}
                  {remainingDistance !== null && (
                    <div className="text-[9px] font-mono text-amber-400 font-bold mt-0.5">
                      {remainingDistance} km left
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Map canvas view widget */}
          <div id="tracking-map" className="flex-1 w-full bg-slate-950 z-10 rounded-2xl overflow-hidden mt-20 min-h-[35vh]"></div>

          {/* Connection overlays */}
          <div className="absolute top-22 left-6 z-40 bg-slate-955/90 border border-slate-800 px-3 py-1.5 rounded-full shadow-lg text-[8px] font-mono tracking-widest font-bold flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${isApiMode ? 'bg-emerald-500 animate-ping' : 'bg-amber-500 animate-pulse'}`}></span>
            <span className="text-slate-400">{isApiMode ? 'CONNECTED API' : 'OFFLINE ENGINE'}</span>
          </div>

          {/* Persistent Logs bottom Drawer Overlay */}
          <div className="bg-slate-900/95 backdrop-blur-md border-t border-slate-800 p-4 rounded-t-3xl shadow-[0_-12px_30px_rgba(0,0,0,0.6)] z-30 flex flex-col gap-3 mt-4">
            
            {/* Drawer Tab Headers */}
            <div className="flex border-b border-slate-800 pb-2 mb-1 justify-between items-center select-none">
              <div className="flex gap-2">
                <button
                  onClick={() => setConsoleTab("logs")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[9px] font-bold font-mono tracking-wider transition duration-150 ${
                    consoleTab === "logs" 
                      ? "bg-slate-800 text-emerald-400 border border-emerald-500/20 shadow-md"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  <Terminal className="w-3.5 h-3.5" />
                  <span>AGENT LOGS</span>
                </button>
                <button
                  onClick={() => setConsoleTab("matchmaker")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[9px] font-bold font-mono tracking-wider transition duration-150 relative ${
                    consoleTab === "matchmaker" 
                      ? "bg-slate-800 text-teal-400 border border-teal-500/20 shadow-md"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5 animate-pulse" />
                  <span>DECISION MATRIX</span>
                  {hospitalMatches.length > 0 && (
                    <span className="absolute -top-1 -right-1 flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500"></span>
                    </span>
                  )}
                </button>
              </div>
              <div className="flex items-center gap-1 text-[8px] font-mono font-bold text-slate-600 animate-pulse uppercase">
                <span className="w-1 h-1 rounded-full bg-slate-600"></span>
                <span>STREAMING DECI-LOOP</span>
              </div>
            </div>

            {/* Tab Content Area */}
            {consoleTab === "logs" ? (
              <div className="font-mono text-[10px] text-emerald-400 bg-black/80 border border-slate-800/80 p-3 h-32 overflow-y-auto flex flex-col gap-1.5 leading-relaxed rounded-xl">
                {agentLogs.length === 0 ? (
                  <div className="text-slate-600 italic text-center py-8 text-[10px]">
                    [TriageAgent] Ingesting parameters...
                  </div>
                ) : (
                  <div className="space-y-1">
                    {agentLogs.map((log, idx) => (
                      <div key={idx} className="border-l border-emerald-500/20 pl-2 text-[10px]">
                        {log}
                      </div>
                    ))}
                    <div ref={terminalEndRef} />
                  </div>
                )}
              </div>
            ) : (
              <div className="h-32 overflow-y-auto flex flex-col gap-2 p-1 font-mono text-[10px]">
                {hospitalMatches.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-4 text-center text-slate-500 gap-1.5 select-none">
                    <Activity className="w-5 h-5 text-slate-600 animate-pulse" />
                    <div className="text-[9px] font-bold text-slate-400">AGENT SELECTION ENGINE IDLE</div>
                    <div className="text-[8px] text-slate-600 max-w-[280px]">
                      Orchestrating concentric ring search algorithms. Awaiting agent decision sequences...
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {hospitalMatches.map((h, idx) => (
                      <div 
                        key={idx} 
                        className={`flex flex-col p-2.5 rounded-xl border transition duration-200 ${
                          h.status === "Selected"
                            ? "bg-emerald-950/40 border-emerald-500/35 shadow-[0_0_10px_rgba(16,185,129,0.1)]"
                            : h.status === "Rejected"
                            ? "bg-slate-900/60 border-slate-800/80 hover:border-slate-800 opacity-65"
                            : "bg-amber-950/20 border-amber-500/30 animate-pulse"
                        }`}
                      >
                        {/* Hospital Title + State */}
                        <div className="flex justify-between items-start gap-2">
                          <div className="text-left">
                            <div className={`font-bold text-[10px] leading-tight ${h.status === "Selected" ? "text-emerald-300" : h.status === "Rejected" ? "text-slate-300" : "text-amber-300"}`}>
                              {h.name}
                            </div>
                            <div className="text-[7px] text-slate-500 mt-0.5">
                              ID: {h.id} • {h.distance !== "-" ? `${h.distance} km away` : "Calculating ETA..."}
                            </div>
                          </div>
                          
                          {/* Status Badge */}
                          <div>
                            {h.status === "Selected" ? (
                              <span className="inline-flex items-center gap-0.5 px-2 py-0.5 text-[8px] font-bold uppercase rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-[0_0_6px_rgba(16,185,129,0.2)]">
                                <CheckCircle2 className="w-2.5 h-2.5" />
                                <span>ACCEPTED</span>
                              </span>
                            ) : h.status === "Rejected" ? (
                              <span className="inline-flex items-center gap-0.5 px-2 py-0.5 text-[8px] font-bold uppercase rounded bg-red-500/10 text-red-400 border border-red-500/20">
                                <AlertTriangle className="w-2.5 h-2.5" />
                                <span>BYPASSED</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-0.5 px-2 py-0.5 text-[8px] font-bold uppercase rounded bg-amber-500/15 text-amber-400 border border-amber-500/30 animate-pulse">
                                <Clock className="w-2.5 h-2.5 animate-spin" />
                                <span>CHECKING</span>
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Resource Grid / Fit Reason */}
                        <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-900 text-[8px] text-slate-400">
                          <div className="flex gap-3">
                            <div>Beds: <span className="font-bold text-slate-300">{h.beds}</span></div>
                            <div>ICU: <span className="font-bold text-slate-300">{h.icu}</span></div>
                            <div>Vents: <span className="font-bold text-slate-300">{h.vents}</span></div>
                          </div>
                          <div className={`font-mono text-[7px] tracking-tight ${h.status === "Selected" ? "text-emerald-400 font-bold" : "text-red-400/80"}`}>
                            {h.reason}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Simulation controls */}
            <div className="flex gap-1.5 pt-1 justify-between select-none">
              <button
                onClick={resetAll}
                className="flex-1 bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-400 py-2 rounded-xl text-[9px] font-bold font-mono transition duration-150 active:scale-95 flex items-center justify-center"
              >
                <span>RESET</span>
              </button>
              
              {currentStatus !== "admitted" && currentStatus !== "warning" && (
                <>
                  <button
                    onClick={stepSimulationTick}
                    className="flex-1 bg-amber-950/70 border border-amber-500/30 hover:border-amber-400 text-amber-300 py-2 rounded-xl text-[9px] font-bold font-mono transition duration-150 active:scale-95 flex items-center justify-center gap-0.5"
                  >
                    <span>STEP TICK</span>
                    <ArrowRight className="w-3 h-3 animate-pulse" />
                  </button>

                  {currentStatus === "dispatched" ? (
                    <button
                      onClick={triggerArrivePatient}
                      className="flex-1 bg-amber-950/70 border border-amber-500/30 hover:border-amber-400 text-amber-300 py-2 rounded-xl text-[9px] font-bold font-mono transition duration-150 active:scale-95 flex items-center justify-center gap-0.5"
                      title="Arrive at Patient Location"
                    >
                      <span>⚡ ARRIVED AT PATIENT</span>
                    </button>
                  ) : (
                    <button
                      onClick={triggerArriveHospital}
                      className="flex-1 bg-emerald-950/70 border border-emerald-500/30 hover:border-emerald-400 text-emerald-300 py-2 rounded-xl text-[9px] font-bold font-mono transition duration-150 active:scale-95 flex items-center justify-center gap-0.5"
                      title="Arrive at Destination Hospital"
                    >
                      <span>⚡ ARRIVED AT HOSPITAL</span>
                    </button>
                  )}
                </>
              )}
            </div>

          </div>

        </div>
      )}

    </div>
  );
}
