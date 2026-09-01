import React from 'react';
import { ShieldCheck, Activity, Power, Lock, Cpu, Sparkles } from 'lucide-react';

export default function Header({ activeTab, setActiveTab, killSwitchEngaged, onToggleKillSwitch }) {
  return (
    <header className="sticky top-0 z-50 bg-[#07090E]/90 backdrop-blur-md border-b border-[#1F2839] px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Brand & Logo */}
        <div className="flex items-center gap-4">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 via-indigo-600 to-cyan-500 shadow-lg shadow-blue-500/20 text-white font-bold text-lg tracking-wider">
            ⚡
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-extrabold text-xl tracking-tight text-white flex items-center gap-1.5">
                BACKSTOP
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">
                  v1.0
                </span>
              </h1>
            </div>
            <p className="text-xs text-slate-400 font-medium">
              Deterministic Policy-Gated AI Revenue Recovery Engine • Track 03
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center bg-[#0F131C] p-1 rounded-xl border border-[#1F2839]">
          <button
            onClick={() => setActiveTab('cohort')}
            className={`px-4 py-2 text-xs font-semibold rounded-lg flex items-center gap-2 transition-all ${
              activeTab === 'cohort'
                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            Cohort Benchmark
          </button>

          <button
            onClick={() => setActiveTab('timeline')}
            className={`px-4 py-2 text-xs font-semibold rounded-lg flex items-center gap-2 transition-all ${
              activeTab === 'timeline'
                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            Case Lifecycle Rail
          </button>

          <button
            onClick={() => setActiveTab('policy')}
            className={`px-4 py-2 text-xs font-semibold rounded-lg flex items-center gap-2 transition-all ${
              activeTab === 'policy'
                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            Compliance Cage (14 Rules)
          </button>

          <button
            onClick={() => setActiveTab('security')}
            className={`px-4 py-2 text-xs font-semibold rounded-lg flex items-center gap-2 transition-all ${
              activeTab === 'security'
                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
            }`}
          >
            <Lock className="w-3.5 h-3.5" />
            Audit Ledger & Kill Switch
          </button>
        </nav>

        {/* Status Indicators & Kill Switch Button */}
        <div className="flex items-center gap-3">
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0F131C] border border-[#1F2839] text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-slate-400">Policy:</span>
            <span className="font-mono text-slate-200 font-semibold">2026.09.01</span>
          </div>

          <button
            onClick={onToggleKillSwitch}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg border flex items-center gap-1.5 transition-all shadow-md ${
              killSwitchEngaged
                ? 'bg-red-950/80 text-red-300 border-red-500/50 hover:bg-red-900'
                : 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40 hover:bg-emerald-900'
            }`}
          >
            <Power className="w-3.5 h-3.5" />
            {killSwitchEngaged ? 'KILL SWITCH ENGAGED' : 'AGENT ACTIVE'}
          </button>
        </div>

      </div>
    </header>
  );
}
