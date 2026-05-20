import React, { useState, useRef, useEffect } from 'react';
import L from 'leaflet';
import { Globe, Cloud, Car, Activity, CheckCircle2, ChevronDown, ChevronUp, Send, Loader2, Terminal, AlertTriangle, Languages, Wind, Thermometer, Droplets } from 'lucide-react';

const BACKEND_URL = "https://irbazmemon123-crisis-intelligence-response-orche-28b6ea0.hf.space";

const CITY_COORDS = {
  Karachi:    { lat: 24.8607, lng: 67.0011 },
  Lahore:     { lat: 31.5204, lng: 74.3587 },
  Islamabad:  { lat: 33.6844, lng: 73.0479 },
  Rawalpindi: { lat: 33.5651, lng: 73.0169 },
  Peshawar:   { lat: 34.0151, lng: 71.5249 },
  Quetta:     { lat: 30.1798, lng: 66.9750 },
};

const CITY_OPTIONS = [
  { name: 'کراچی (Karachi)',       value: 'Karachi' },
  { name: 'لاہور (Lahore)',        value: 'Lahore' },
  { name: 'اسلام آباد (Islamabad)',value: 'Islamabad' },
  { name: 'راولپنڈی (Rawalpindi)', value: 'Rawalpindi' },
  { name: 'پشاور (Peshawar)',      value: 'Peshawar' },
  { name: 'کوئٹہ (Quetta)',        value: 'Quetta' },
];

const SIGNAL_PRESETS = {
  flood:          ['G-10 mein pani bhar gaya hai, gaariyan phans gayi hain', 'Flash flood happening at George Town for past 30 mins, streets submerged'],
  fire:           ['Aag lag gayi garment factory mein, dhuaan poori building mein phal raha hai', 'Massive fire near Saddar market, fire brigade needed!'],
  accident:       ['Shadeed hadsa M2 motorway pe, 3 gaariyan takra gayi, zakmi hain', 'Head-on collision near Gulshan chowrangi, road blocked'],
  heatwave:       ['Karachi mein garmi 47 degrees, log behosh ho rahe hain', 'Extreme heat stroke cases in Lahore today, hospital full'],
  infrastructure: ['Bijli subah se gaya hai, hospital ka generator bhi band', 'Major power outage in Orangi Town — 6 hours hue'],
  disinformation: ['Clifton 5 mein pani bhara hua hai', 'Gulshan mein heavy flood hai, completely submerged!'],
};

const CRISIS_CFG = {
  flood:          { ring: 'border-blue-500/40',   badge: 'bg-blue-500/20 text-blue-300',   icon: '🌊' },
  fire:           { ring: 'border-red-500/40',    badge: 'bg-red-500/20 text-red-300',     icon: '🔥' },
  accident:       { ring: 'border-amber-500/40',  badge: 'bg-amber-500/20 text-amber-300', icon: '🚗' },
  heatwave:       { ring: 'border-orange-500/40', badge: 'bg-orange-500/20 text-orange-300',icon: '☀️' },
  infrastructure: { ring: 'border-purple-500/40', badge: 'bg-purple-500/20 text-purple-300',icon: '⚡' },
  disinformation: { ring: 'border-slate-500/40',  badge: 'bg-slate-500/20 text-slate-300', icon: '🚫' },
};

const SEV = {
  CRITICAL: 'bg-red-600/30 text-red-300 border border-red-600/50',
  HIGH:     'bg-orange-600/30 text-orange-300 border border-orange-600/50',
  MEDIUM:   'bg-amber-600/30 text-amber-300 border border-amber-600/50',
  LOW:      'bg-slate-600/30 text-slate-400 border border-slate-600/50',
};

const WX_CODE = (c) => {
  if (c === 0) return { label: 'Clear Sky', icon: '☀️' };
  if (c <= 2)  return { label: 'Partly Cloudy', icon: '⛅' };
  if (c <= 49) return { label: 'Overcast / Fog', icon: '🌫️' };
  if (c <= 67) return { label: 'Rain', icon: '🌧️' };
  if (c <= 77) return { label: 'Snow', icon: '❄️' };
  if (c <= 82) return { label: 'Rain Showers', icon: '🌦️' };
  return { label: 'Thunderstorm', icon: '⛈️' };
};

export default function CrisisDashboard() {
  const [posts, setPosts]               = useState(SIGNAL_PRESETS.flood);
  const [newPost, setNewPost]           = useState('');
  const [city, setCity]                 = useState('Karachi');
  const [inclWeather, setInclWeather]   = useState(true);
  const [inclTraffic, setInclTraffic]   = useState(true);
  const [loading, setLoading]           = useState(false);
  const [result, setResult]             = useState(null);
  const [showTrace, setShowTrace]       = useState(false);
  const [preset, setPreset]             = useState('flood');
  const [liveWx, setLiveWx]            = useState(null);
  const [wxLoading, setWxLoading]       = useState(false);
  const [lang, setLang]                 = useState('en');

  const mapRef      = useRef(null);
  const mapInst     = useRef(null);
  const markerRef   = useRef(null);
  const resultRef   = useRef(null);

  // Fetch real weather on city change
  useEffect(() => {
    const coords = CITY_COORDS[city];
    if (!coords) return;
    setWxLoading(true);
    fetch(`https://api.open-meteo.com/v1/forecast?latitude=${coords.lat}&longitude=${coords.lng}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,precipitation`)
      .then(r => r.json())
      .then(d => { setLiveWx(d.current); setWxLoading(false); })
      .catch(() => setWxLoading(false));
  }, [city]);

  // Init Leaflet map
  useEffect(() => {
    if (!mapRef.current || mapInst.current) return;
    const coords = CITY_COORDS[city] || CITY_COORDS.Karachi;
    const m = L.map(mapRef.current, { zoomControl: true, scrollWheelZoom: false })
      .setView([coords.lat, coords.lng], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(m);
    mapInst.current = m;
    addMarker(coords, city, '🛡');
  }, []);

  // Re-center map when city changes
  useEffect(() => {
    const coords = CITY_COORDS[city];
    if (!mapInst.current || !coords) return;
    mapInst.current.setView([coords.lat, coords.lng], 12);
    addMarker(coords, city, '📍');
  }, [city]);

  // Fly to crisis zone after analysis
  useEffect(() => {
    if (!result || !mapInst.current) return;
    const coords = CITY_COORDS[result.city] || CITY_COORDS.Karachi;
    mapInst.current.flyTo([coords.lat, coords.lng], 13, { duration: 1.5 });
    const cfg = CRISIS_CFG[result.crisis_type] || {};
    addMarker(coords, `${cfg.icon || '⚠️'} ${result.crisis_type?.toUpperCase()} — ${result.severity}`, cfg.icon || '⚠️');
    resultRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [result]);

  const addMarker = (coords, label, emoji) => {
    if (markerRef.current) markerRef.current.remove();
    const icon = L.divIcon({
      html: `<div style="font-size:24px;line-height:1;filter:drop-shadow(0 0 6px rgba(16,185,129,0.8))">${emoji}</div>`,
      className: '', iconAnchor: [12, 12],
    });
    markerRef.current = L.marker([coords.lat, coords.lng], { icon })
      .addTo(mapInst.current)
      .bindPopup(`<b style="font-family:monospace;color:#10b981">${label}</b>`)
      .openPopup();
  };

  const loadPreset = (key) => { setPreset(key); setPosts(SIGNAL_PRESETS[key]); };

  const runAnalysis = async () => {
    if (!posts.length) return;
    setLoading(true); setResult(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/crisis/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ social_posts: posts, city, include_weather: inclWeather, include_traffic: inclTraffic }),
      });
      if (!res.ok) throw new Error();
      setResult(await res.json());
    } catch {
      setResult({ error: '⚠️ Backend offline. Run: uvicorn main:app --port 8000' });
    }
    setLoading(false);
  };

  const wx   = liveWx ? WX_CODE(liveWx.weather_code) : null;
  const cfg  = result && CRISIS_CFG[result.crisis_type] ? CRISIS_CFG[result.crisis_type] : { ring: 'border-slate-700', badge: 'bg-slate-700 text-slate-300', icon: '🛡' };

  return (
    <div className="w-full bg-slate-950 text-slate-100 font-mono">

      {/* Header */}
      <div className="bg-slate-900/70 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-emerald-400 animate-pulse" />
          <span className="font-bold text-emerald-400 text-xs tracking-widest">CRISIS INTELLIGENCE</span>
        </div>
        <button onClick={() => setLang(l => l === 'en' ? 'ur' : 'en')}
          className="flex items-center gap-1 bg-slate-800 border border-slate-700 hover:border-emerald-500/40 px-2 py-1 rounded-lg text-[10px] text-slate-300 transition-all">
          <Languages className="w-3 h-3" />
          {lang === 'en' ? 'اردو' : 'English'}
        </button>
      </div>

      <div className="px-3 py-3 space-y-3">

        {/* Live Weather Card */}
        <div className="bg-gradient-to-r from-blue-950/40 to-slate-900/60 border border-blue-500/30 rounded-2xl p-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] text-blue-400 uppercase tracking-widest font-bold">
              {lang === 'ur' ? 'موجودہ موسم' : 'Live Weather'} — {city}
            </p>
            {wxLoading && <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />}
          </div>
          {wx && liveWx ? (
            <div className="grid grid-cols-4 gap-2">
              <div className="text-center">
                <p className="text-2xl">{wx.icon}</p>
                <p className="text-[8px] text-slate-400 mt-0.5">{wx.label}</p>
              </div>
              <div className="text-center">
                <p className="text-sm font-bold text-amber-300">{liveWx.temperature_2m}°C</p>
                <p className="text-[8px] text-slate-500">Temperature</p>
              </div>
              <div className="text-center">
                <p className="text-sm font-bold text-blue-300">{liveWx.relative_humidity_2m}%</p>
                <p className="text-[8px] text-slate-500">Humidity</p>
              </div>
              <div className="text-center">
                <p className="text-sm font-bold text-emerald-300">{liveWx.wind_speed_10m}</p>
                <p className="text-[8px] text-slate-500">km/h Wind</p>
              </div>
            </div>
          ) : !wxLoading && (
            <p className="text-[10px] text-slate-500">Fetching weather data...</p>
          )}
        </div>

        {/* Map */}
        <div className="rounded-2xl overflow-hidden border border-slate-700" style={{ height: '200px' }}>
          <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
        </div>

        {/* Preset Buttons */}
        <div>
          <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1.5">
            {lang === 'ur' ? 'بحران کی قسم' : 'Crisis Presets'}
          </p>
          <div className="grid grid-cols-6 gap-1">
            {Object.entries(CRISIS_CFG).map(([key, c]) => (
              <button key={key} onClick={() => loadPreset(key)}
                className={`py-2 rounded-lg text-base flex items-center justify-center border transition-all ${preset === key ? c.ring + ' bg-slate-900/60' : 'border-slate-800 hover:border-slate-600'}`}
                title={key}>{c.icon}
              </button>
            ))}
          </div>
        </div>

        {/* City Selector */}
        <select value={city} onChange={e => setCity(e.target.value)}
          className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-xs px-3 py-2 rounded-xl focus:outline-none focus:border-emerald-500/40">
          {CITY_OPTIONS.map(c => <option key={c.value} value={c.value}>{c.name}</option>)}
        </select>

        {/* API Toggles */}
        <div className="flex gap-2">
          <button onClick={() => setInclWeather(v => !v)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-xl text-[10px] font-bold border transition-all ${inclWeather ? 'bg-blue-950/40 border-blue-500/40 text-blue-300' : 'bg-slate-900 border-slate-800 text-slate-500'}`}>
            <Cloud className="w-3 h-3" />{lang === 'ur' ? 'موسم' : 'Weather'}
          </button>
          <button onClick={() => setInclTraffic(v => !v)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-xl text-[10px] font-bold border transition-all ${inclTraffic ? 'bg-amber-950/40 border-amber-500/40 text-amber-300' : 'bg-slate-900 border-slate-800 text-slate-500'}`}>
            <Car className="w-3 h-3" />{lang === 'ur' ? 'ٹریفک' : 'Traffic'}
          </button>
        </div>

        {/* Signal Posts */}
        <div>
          <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1.5">
            {lang === 'ur' ? 'سوشل میڈیا سگنل' : 'Social Media Signals'}
          </p>
          <div className="space-y-1.5 mb-2">
            {posts.map((p, i) => (
              <div key={i} className="flex items-start gap-2 bg-slate-900/60 border border-slate-800 rounded-lg px-2.5 py-2">
                <span className="text-[9px] text-emerald-500 mt-0.5 shrink-0">📡</span>
                <p className="text-[11px] text-slate-300 flex-1 leading-relaxed" dir="auto">{p}</p>
                <button onClick={() => setPosts(prev => prev.filter((_, j) => j !== i))} className="text-slate-600 hover:text-red-400 text-[10px] shrink-0">✕</button>
              </div>
            ))}
          </div>
          <div className="flex gap-1.5">
            <input type="text" value={newPost} onChange={e => setNewPost(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && newPost.trim() && (setPosts(p => [...p, newPost.trim()]), setNewPost(''))}
              placeholder={lang === 'ur' ? 'اردو یا انگریزی میں لکھیں...' : 'Type in English or Urdu...'}
              className="flex-1 bg-slate-900 border border-slate-700 text-slate-200 text-[11px] px-2.5 py-1.5 rounded-lg focus:outline-none focus:border-emerald-500/40" dir="auto" />
            <button onClick={() => newPost.trim() && (setPosts(p => [...p, newPost.trim()]), setNewPost(''))}
              className="bg-emerald-900/40 border border-emerald-500/30 text-emerald-400 px-2.5 py-1.5 rounded-lg hover:border-emerald-400">
              <Send className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Run Button */}
        <button onClick={runAnalysis} disabled={loading || !posts.length}
          className={`w-full py-3 rounded-2xl font-bold text-xs tracking-widest border flex items-center justify-center gap-2 transition-all ${loading ? 'bg-slate-900 border-slate-700 text-slate-500' : 'bg-emerald-950/40 border-emerald-500/40 hover:border-emerald-400 text-emerald-300 active:scale-95'}`}>
          {loading ? <><Loader2 className="w-4 h-4 animate-spin" />{lang === 'ur' ? 'تجزیہ ہو رہا ہے...' : 'ANALYZING...'}</> : <><Activity className="w-4 h-4" />{lang === 'ur' ? 'بحران کا تجزیہ کریں' : 'RUN CRISIS ANALYSIS'}</>}
        </button>

        {/* Results */}
        {result && !result.error && (
          <div ref={resultRef} className={`border ${cfg.ring} rounded-2xl overflow-hidden`}>
            <div className={`border-b ${cfg.ring} px-3 py-2.5 flex items-center justify-between`}>
              <div className="flex items-center gap-2">
                <span className="text-xl">{cfg.icon}</span>
                <div>
                  <p className="text-xs font-bold text-slate-200 uppercase tracking-wider">{result.crisis_type} DETECTED</p>
                  <p className="text-[10px] text-slate-500">{result.city} • {result.timestamp}</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${SEV[result.severity] || SEV.MEDIUM}`}>{result.severity}</span>
                <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-emerald-900/30 text-emerald-400 border border-emerald-500/30">{result.confidence}%</span>
              </div>
            </div>

            {/* Urdu Alert */}
            <div className="bg-amber-950/20 border-b border-amber-500/20 px-3 py-2 text-center" dir="rtl">
              <p className="text-sm text-amber-300 font-bold">{result.urdu_alert}</p>
            </div>

            {/* Validated Signals */}
            {result.validated_signals && (
              <div className="border-b border-slate-800 p-3 space-y-2">
                <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">Signal Verification (Satellite/Weather)</p>
                {result.validated_signals.map((sig, idx) => (
                  <div key={idx} className={`p-2.5 rounded-xl border text-[10px] ${sig.is_valid ? 'bg-emerald-950/25 border-emerald-500/30 text-emerald-300' : 'bg-red-950/25 border-red-500/30 text-red-300'}`}>
                    <div className="flex items-center justify-between font-bold mb-1">
                      <span>Signal #{idx+1}: {sig.is_valid ? '✅ VERIFIED REAL' : '⚠️ FAKE / FALSE INFO'}</span>
                      <span className="text-[8px] text-slate-500 uppercase">{sig.location}</span>
                    </div>
                    <p className="text-slate-400 mb-1 leading-relaxed">"{sig.post}"</p>
                    <p className={`text-[8.5px] font-bold ${sig.is_valid ? 'text-emerald-400' : 'text-red-400'}`}>{sig.reason}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="p-3 space-y-3">
              {/* Matched Keywords */}
              <div className="flex flex-wrap gap-1">
                {result.matched_signals?.map((s, i) => (
                  <span key={i} className={`text-[9px] px-2 py-0.5 rounded-full ${cfg.badge}`}>{s}</span>
                ))}
              </div>

              {/* Weather + Traffic cards */}
              <div className="grid grid-cols-2 gap-2">
                {result.weather_signal && (
                  <div className="bg-blue-950/20 border border-blue-500/20 rounded-xl p-2">
                    <p className="text-[9px] text-blue-400 font-bold mb-1">🌡 WEATHER</p>
                    <p className="text-[10px] text-slate-300">{result.weather_signal.condition?.toUpperCase()}</p>
                    <p className="text-[9px] text-slate-500">{result.weather_signal.temp_c}°C • {result.weather_signal.rainfall_mm}mm</p>
                  </div>
                )}
                {result.traffic_signal && (
                  <div className="bg-amber-950/20 border border-amber-500/20 rounded-xl p-2">
                    <p className="text-[9px] text-amber-400 font-bold mb-1">🚦 TRAFFIC</p>
                    <p className="text-[10px] text-slate-300">{result.traffic_signal.congestion_level?.toUpperCase()}</p>
                    <p className="text-[9px] text-slate-500">{result.traffic_signal.avg_speed_kmh} km/h</p>
                  </div>
                )}
              </div>

              {/* Impacts */}
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{lang === 'ur' ? 'متوقع اثرات' : 'Impact Assessment'}</p>
                {result.impacts?.map((imp, i) => (
                  <div key={i} className="flex items-start gap-2 text-[10px] text-slate-400 mb-0.5">
                    <AlertTriangle className="w-3 h-3 text-amber-500 mt-0.5 shrink-0" />{imp}
                  </div>
                ))}
              </div>

              {/* Before / After */}
              <div className="grid grid-cols-2 gap-1.5">
                <div className="bg-red-950/20 border border-red-800/30 rounded-xl p-2">
                  <p className="text-[9px] text-red-400 font-bold mb-1">BEFORE</p>
                  {result.before_state && Object.entries(result.before_state).map(([k, v]) => (
                    <div key={k}><p className="text-[8px] text-slate-500">{k.replace(/_/g,' ')}</p><p className="text-[9px] text-slate-300 mb-0.5">{v}</p></div>
                  ))}
                </div>
                <div className="bg-emerald-950/20 border border-emerald-800/30 rounded-xl p-2">
                  <p className="text-[9px] text-emerald-400 font-bold mb-1">AFTER</p>
                  {result.after_state && Object.entries(result.after_state).map(([k, v]) => (
                    <div key={k}><p className="text-[8px] text-slate-500">{k.replace(/_/g,' ')}</p><p className="text-[9px] text-slate-300 mb-0.5">{v}</p></div>
                  ))}
                </div>
              </div>

              {/* Response Actions */}
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{lang === 'ur' ? 'جوابی اقدامات' : 'Response Actions'}</p>
                {result.response_actions?.map((a, i) => (
                  <div key={i} className="flex items-start gap-2 mb-1">
                    <div className="w-4 h-4 rounded-full bg-emerald-900/40 border border-emerald-500/30 flex items-center justify-center shrink-0 mt-0.5">
                      <span className="text-[8px] text-emerald-400 font-bold">{i+1}</span>
                    </div>
                    <p className="text-[10px] text-slate-300">{a}</p>
                  </div>
                ))}
              </div>

              {/* Execution Log */}
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-1">{lang === 'ur' ? 'عملدرآمد لاگ' : 'Execution Log'}</p>
                {result.execution_log?.map((e, i) => (
                  <div key={i} className="flex items-center gap-2 text-[9px] mb-0.5">
                    <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />
                    <span className="text-emerald-400">{e.timestamp}</span>
                    <span className="text-slate-400 flex-1 truncate">{e.action}</span>
                    <span className="text-slate-600">{e.simulated_delay_ms}ms</span>
                  </div>
                ))}
              </div>

              {/* Agent Trace */}
              <button onClick={() => setShowTrace(v => !v)}
                className="w-full flex items-center justify-between px-2 py-1.5 bg-slate-900/50 border border-slate-800 rounded-lg text-[10px] text-slate-400 hover:border-slate-700">
                <div className="flex items-center gap-1.5"><Terminal className="w-3 h-3" />Agent Trace</div>
                {showTrace ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
              {showTrace && (
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-2 max-h-40 overflow-y-auto">
                  {result.trace_logs?.map((log, i) => (
                    <div key={i} className="text-[9px] border-l border-emerald-500/20 pl-2 mb-0.5">
                      <span className="text-emerald-500/70">[{log.timestamp}] </span>
                      <span className="text-slate-400">{log.message}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {result?.error && (
          <div className="bg-red-950/30 border border-red-500/30 rounded-xl p-3 text-center text-red-400 text-xs">{result.error}</div>
        )}
      </div>
    </div>
  );
}
