import React, { useState } from 'react';
import EmergencyDashboard from './components/EmergencyDashboard';
import CrisisDashboard from './components/CrisisDashboard';
import { ShieldAlert, Globe, Ambulance, AlertTriangle } from 'lucide-react';

const TABS = [
  {
    id: "emergency",
    label: "ایمبولینس",
    labelEn: "Emergency Dispatch",
    icon: "🚑",
  },
  {
    id: "crisis",
    label: "بحران",
    labelEn: "Crisis Intelligence",
    icon: "🛡",
  }
];

export default function App() {
  const [activeTab, setActiveTab] = useState("emergency");
  const [lang, setLang] = useState("en"); // en | ur

  return (
    <div className="w-screen min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center p-2 relative font-sans overflow-x-hidden">

      {/* Background glow effects */}
      <div className="fixed inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:5rem_5rem] opacity-25 [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_80%,transparent_100%)] pointer-events-none z-0" />
      <div className="fixed top-1/4 left-1/4 w-96 h-96 rounded-full bg-red-600/10 blur-[100px] pointer-events-none animate-pulse z-0" />
      <div className="fixed bottom-1/4 right-1/4 w-96 h-96 rounded-full bg-emerald-600/10 blur-[100px] pointer-events-none animate-pulse z-0" style={{ animationDelay: '2s' }} />

      {/* ── Header Bar ── */}
      <div className="z-10 w-full max-w-md mb-3">
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl px-4 py-2.5 flex items-center justify-between backdrop-blur">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-500 animate-pulse" />
            <div>
              <h1 className="font-orbitron font-extrabold text-sm tracking-[0.15em] text-slate-200 leading-none">
                CIRO PLATFORM
              </h1>
              <p className="text-[9px] text-slate-500 font-mono tracking-widest">
                {lang === "ur" ? "بحران انٹیلی جنس سسٹم" : "Crisis Intelligence & Response Orchestrator"}
              </p>
            </div>
          </div>
          <button
            onClick={() => setLang(l => l === "en" ? "ur" : "en")}
            className="text-[10px] bg-slate-800 border border-slate-700 hover:border-emerald-500/40 px-2 py-1 rounded-lg text-slate-300 transition-all"
          >
            {lang === "en" ? "اردو" : "EN"}
          </button>
        </div>
      </div>

      {/* ── Tab Switcher ── */}
      <div className="z-10 w-full max-w-md mb-3">
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-1 flex gap-1 backdrop-blur">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-bold tracking-widest transition-all ${
                activeTab === tab.id
                  ? "bg-emerald-950/60 border border-emerald-500/40 text-emerald-300"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              <span>{tab.icon}</span>
              <span>{lang === "ur" ? tab.label : tab.labelEn}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Main Content ── */}
      <div className="z-10 w-full max-w-md relative">
        {activeTab === "emergency" && (
          <div className="relative">
            <div className="absolute -inset-1 rounded-[50px] bg-gradient-to-tr from-slate-900 via-slate-800 to-slate-900 blur-sm opacity-50 z-0" />
            <div className="relative z-10">
              <EmergencyDashboard />
            </div>
          </div>
        )}
        {activeTab === "crisis" && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-3xl overflow-hidden backdrop-blur">
            <CrisisDashboard />
          </div>
        )}
      </div>

      {/* ── Footer ── */}
      <div className="mt-4 text-center text-[9px] text-slate-700 font-mono tracking-wider z-10">
        GOOGLE ANTIGRAVITY AGENTIC PIPELINE • HACKATHON DEMO • CIRO v2.0
      </div>

    </div>
  );
}
