import React, { useState, useEffect } from 'react';
import { ShieldCheck, Scale, FileText, CheckCircle2, Info, BookOpen } from 'lucide-react';

export default function PolicyScreen() {
  const [policies, setPolicies] = useState([]);

  useEffect(() => {
    fetch('http://localhost:8000/api/policies')
      .then(r => r.json())
      .then(data => setPolicies(data.rules || []))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="glass-panel p-6 bg-gradient-to-r from-indigo-950/40 via-[#0F131C] to-blue-950/30">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold mb-3">
              <Scale className="w-3.5 h-3.5" />
              Machine-Executable Regulatory Compliance Cage
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              14 Deterministic Compliance & Anti-Spam Rules
            </h2>
            <p className="text-sm text-slate-400 mt-1 max-w-3xl">
              Grounded in the RBI Digital Payments — E-mandate Framework (Notified 21 April 2026), TRAI Telecom Commercial Communications Regulations, and DPDP Act 2023.
            </p>
          </div>

          <div className="text-xs font-mono px-3 py-2 rounded-lg bg-[#1B2332] text-slate-300 border border-[#2E3B52] flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            Policy Version: 2026.09.01
          </div>
        </div>
      </div>

      {/* Grid of 14 Rules */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {policies.map(rule => (
          <div key={rule.id} className="glass-panel p-5 border-[#1F2839] hover:border-blue-500/40 transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-blue-400 px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20">
                  {rule.id}
                </span>
                <span className="text-[11px] font-mono text-slate-400 px-2 py-0.5 rounded bg-[#1B2332]">
                  {rule.type}
                </span>
              </div>

              <h4 className="font-bold text-sm text-white mt-3">{rule.name}</h4>
              <p className="text-xs text-slate-300 mt-2 leading-relaxed">{rule.desc}</p>
            </div>

            <div className="mt-4 pt-3 border-t border-[#1F2839] flex items-center justify-between text-[11px]">
              <span className="text-slate-500 flex items-center gap-1">
                <BookOpen className="w-3 h-3 text-slate-400" />
                Citation:
              </span>
              <span className="text-slate-300 font-mono font-medium truncate max-w-[200px]">{rule.citation}</span>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}
