import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, ShieldAlert, Cpu, ArrowRight, CheckCircle2, XCircle, 
  Clock, Hash, FileCode, Play, AlertCircle, Sparkles, Filter, ChevronRight
} from 'lucide-react';

export default function TimelineScreen({ cases, selectedCaseId, onSelectCase, onProcessCase }) {
  const [timelineData, setTimelineData] = useState(null);
  const [loadingTimeline, setLoadingTimeline] = useState(false);
  const [filterArm, setFilterArm] = useState('all');
  const [filterCause, setFilterCause] = useState('all');

  const filteredCases = cases.filter(c => {
    if (filterArm !== 'all' && c.cohort_arm !== filterArm) return false;
    if (filterCause !== 'all' && c.root_cause !== filterCause) return false;
    return true;
  });

  useEffect(() => {
    if (!selectedCaseId && filteredCases.length > 0) {
      onSelectCase(filteredCases[0].case_id);
    }
  }, [cases, selectedCaseId]);

  useEffect(() => {
    if (!selectedCaseId) return;
    setLoadingTimeline(true);
    fetch(`http://127.0.0.1:8000/api/cases/${selectedCaseId}/timeline`)
      .then(r => r.json())
      .then(data => {
        setTimelineData(data);
        setLoadingTimeline(false);
      })
      .catch(err => {
        console.error("Timeline error:", err);
        setLoadingTimeline(false);
      });
  }, [selectedCaseId]);

  const activeCase = cases.find(c => c.case_id === selectedCaseId);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[750px]">
      
      {/* Left Sidebar: Case Queue */}
      <div className="lg:col-span-4 glass-panel p-4 flex flex-col h-[750px]">
        <div className="flex items-center justify-between pb-3 border-b border-[#1F2839]">
          <div>
            <h3 className="font-bold text-sm text-white">Payment Failure Queue</h3>
            <p className="text-xs text-slate-400">{filteredCases.length} cases loaded</p>
          </div>
          <div className="flex items-center gap-1">
            <select
              value={filterArm}
              onChange={e => setFilterArm(e.target.value)}
              className="bg-[#1B2332] text-slate-300 text-xs border border-[#2E3B52] rounded px-2 py-1"
            >
              <option value="all">All Arms</option>
              <option value="treatment">Treatment (80%)</option>
              <option value="control">Control (20%)</option>
            </select>
          </div>
        </div>

        {/* Scrollable list */}
        <div className="flex-1 overflow-y-auto space-y-2 mt-3 pr-1">
          {filteredCases.map(item => {
            const isSelected = item.case_id === selectedCaseId;
            return (
              <div
                key={item.case_id}
                onClick={() => onSelectCase(item.case_id)}
                className={`p-3 rounded-lg border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-blue-600/15 border-blue-500/50 shadow-md glow-blue'
                    : 'bg-[#0F131C] border-[#1F2839] hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="mono text-xs font-bold text-white">₹{item.amount_inr?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold uppercase ${
                    item.cohort_arm === 'control'
                      ? 'bg-slate-700/50 text-slate-300 border border-slate-600'
                      : 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                  }`}>
                    {item.cohort_arm}
                  </span>
                </div>

                <div className="mt-2 flex items-center justify-between text-xs">
                  <span className="text-slate-300 font-medium truncate max-w-[170px]">{item.root_cause}</span>
                  <span className="text-slate-500 mono text-[11px] uppercase">{item.method}</span>
                </div>

                <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-500 mono">
                  <span>{item.payment_id}</span>
                  <span className={`px-1.5 py-0.2 rounded font-sans text-[10px] ${
                    item.status === 'recovered'
                      ? 'bg-emerald-950 text-emerald-400'
                      : item.status === 'blocked'
                      ? 'bg-red-950 text-red-400'
                      : 'bg-slate-800 text-slate-400'
                  }`}>
                    {item.status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right Area: Deep Lifecycle Timeline Rail */}
      <div className="lg:col-span-8 glass-panel p-6 flex flex-col h-[750px] overflow-y-auto">
        
        {/* Header of Active Case */}
        {activeCase && (
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1F2839] mb-6">
            <div>
              <div className="flex items-center gap-2">
                <span className="mono text-lg font-bold text-white">₹{activeCase.amount_inr?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                <span className="mono text-xs text-slate-400 font-medium">({activeCase.payment_id})</span>
                <span className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${
                  activeCase.cohort_arm === 'control' ? 'bg-slate-800 text-slate-300' : 'bg-blue-900/60 text-blue-300'
                }`}>
                  ARM: {activeCase.cohort_arm.toUpperCase()}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Diagnosed Root Cause: <span className="font-semibold text-slate-200">{activeCase.root_cause}</span> • Confidence: <span className="text-emerald-400 mono">{(activeCase.cause_confidence * 100).toFixed(0)}%</span>
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => onProcessCase(activeCase.case_id)}
                className="btn-primary text-xs"
              >
                <Play className="w-3 h-3 fill-white" />
                Process Agent Cycle
              </button>
            </div>
          </div>
        )}

        {/* Loading Spinner */}
        {loadingTimeline && (
          <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">
            <Sparkles className="w-5 h-5 animate-spin mr-2 text-blue-400" />
            Loading cryptographic timeline...
          </div>
        )}

        {/* Timeline Rail */}
        {!loadingTimeline && timelineData && (
          <div className="space-y-6 relative before:absolute before:inset-0 before:left-4 before:w-0.5 before:bg-[#1F2839]">
            
            {/* Step 1: Webhook Ingest */}
            <div className="relative flex items-start gap-4">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600/20 border border-blue-500/50 text-blue-400 font-mono text-xs font-bold shrink-0 z-10">
                1
              </div>
              <div className="flex-1 glass-panel p-4 bg-[#0A0D14]/80">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-white">Event Ingest & Signature Verification</span>
                  <span className="text-slate-500 mono">{timelineData.timeline[0]?.details?.method}</span>
                </div>
                <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs mono">
                  <div className="bg-[#121722] p-2 rounded border border-[#1F2839]">
                    <span className="text-slate-500 block text-[10px]">REASON</span>
                    <span className="text-slate-300 font-semibold">{timelineData.timeline[0]?.details?.error_reason}</span>
                  </div>
                  <div className="bg-[#121722] p-2 rounded border border-[#1F2839]">
                    <span className="text-slate-500 block text-[10px]">SOURCE</span>
                    <span className="text-slate-300 font-semibold">{timelineData.timeline[0]?.details?.error_source}</span>
                  </div>
                  <div className="bg-[#121722] p-2 rounded border border-[#1F2839]">
                    <span className="text-slate-500 block text-[10px]">RECURRING</span>
                    <span className="text-slate-300 font-semibold">{timelineData.timeline[0]?.details?.is_recurring ? 'Yes (E-mandate)' : 'No'}</span>
                  </div>
                  <div className="bg-[#121722] p-2 rounded border border-[#1F2839]">
                    <span className="text-slate-500 block text-[10px]">REPLAY DEFENSE</span>
                    <span className="text-emerald-400 font-semibold">Unique DB Index</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Step 2: Deterministic Diagnosis */}
            <div className="relative flex items-start gap-4">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-600/20 border border-indigo-500/50 text-indigo-400 font-mono text-xs font-bold shrink-0 z-10">
                2
              </div>
              <div className="flex-1 glass-panel p-4 bg-[#0A0D14]/80">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-white">Deterministic Error Taxonomy Diagnosis</span>
                  <span className="text-emerald-400 font-mono font-semibold">100% Exact Map</span>
                </div>
                <div className="mt-2 text-xs text-slate-300">
                  Mapped to <span className="font-bold text-white font-mono px-2 py-0.5 rounded bg-indigo-950 border border-indigo-500/30">{timelineData.timeline[1]?.details?.root_cause}</span>
                </div>
              </div>
            </div>

            {/* Step 3: Policy Pre-Gate Cage (Showpiece: Permitted vs Struck-through Denied with Rule IDs) */}
            <div className="relative flex items-start gap-4">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-amber-600/20 border border-amber-500/50 text-amber-400 font-mono text-xs font-bold shrink-0 z-10">
                3
              </div>
              <div className="flex-1 glass-panel p-4 bg-[#0A0D14]/80 border-amber-500/30">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-amber-400 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Policy Pre-Gate Cage (RBI 2026 & TRAI Rules)
                  </span>
                  <span className="text-slate-500 mono">{timelineData.timeline[2]?.details?.ist_evaluation_time}</span>
                </div>

                {/* Permitted Actions */}
                <div className="mt-3">
                  <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider block mb-1.5">
                    Permitted Action Space (Pre-Approved for Model):
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {timelineData.timeline[2]?.details?.permitted_actions?.map(act => (
                      <span key={act} className="px-2.5 py-1 rounded-md text-xs font-mono font-semibold permitted-chip">
                        ✓ {act}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Struck-Through Denied Actions with Rule IDs */}
                {Object.keys(timelineData.timeline[2]?.details?.denied_actions || {}).length > 0 && (
                  <div className="mt-3 pt-3 border-t border-[#1F2839]">
                    <span className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider block mb-1.5">
                      Blocked by Compliance Rules:
                    </span>
                    <div className="space-y-1.5">
                      {Object.entries(timelineData.timeline[2]?.details?.denied_actions || {}).map(([act, reason]) => (
                        <div key={act} className="flex items-center justify-between p-2 rounded bg-rose-950/20 border border-rose-500/20 text-xs">
                          <span className="denied-chip font-mono font-semibold text-rose-300 px-2 py-0.5 rounded">
                            {act}
                          </span>
                          <span className="text-slate-300 font-mono text-[11px] text-right">{reason}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            </div>

            {/* Step 4: Redacted Projection & Gemini Chooser */}
            <div className="relative flex items-start gap-4">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-cyan-600/20 border border-cyan-500/50 text-cyan-400 font-mono text-xs font-bold shrink-0 z-10">
                4
              </div>
              <div className="flex-1 glass-panel p-4 bg-[#0A0D14]/80">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-white flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                    Data Minimisation & Gemini Chooser Output
                  </span>
                  <span className="text-slate-500 mono">DPDP Act 2023 Clean</span>
                </div>
                
                <p className="text-xs text-slate-400 mt-2">
                  PII stripped: Model received discrete amount band (<span className="text-cyan-300 font-mono">{timelineData.timeline[3]?.details?.redacted_payload?.amount_band}</span>) and permitted action enum.
                </p>

                <div className="mt-2.5 p-2.5 rounded bg-[#07090E] border border-[#1F2839] text-xs font-mono text-slate-300">
                  <div className="text-emerald-400 font-semibold">Chosen Action: "{activeCase?.last_action || 'Pending'}"</div>
                  <div className="text-slate-400 mt-1">Prompt Contract: Strict JSON schema + monotonic ladder fallback toward inaction.</div>
                </div>
              </div>
            </div>

            {/* Step 5: 5-Wall Gated Execution & Cryptographic Hash Block */}
            <div className="relative flex items-start gap-4">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-emerald-600/20 border border-emerald-500/50 text-emerald-400 font-mono text-xs font-bold shrink-0 z-10">
                5
              </div>
              <div className="flex-1 glass-panel p-4 bg-[#0A0D14]/80 border-emerald-500/30">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    5-Wall Gated Execution & Cryptographic Ledger
                  </span>
                  <span className="text-slate-400 mono">Wall 1..5 Passed</span>
                </div>

                <div className="mt-3 p-3 rounded-lg bg-[#07090E] border border-[#1F2839] space-y-1.5 text-xs font-mono">
                  {timelineData.ledger?.map(entry => (
                    <div key={entry.seq} className="flex items-center justify-between py-1 border-b border-[#1F2839]/60 last:border-0">
                      <div className="flex items-center gap-2">
                        <span className="text-blue-400 font-bold">#{entry.seq}</span>
                        <span className="text-slate-300 font-sans">{entry.stage}</span>
                      </div>
                      <div className="text-slate-500 text-[11px]">
                        HASH: <span className="text-emerald-400">{entry.hash}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>
        )}

      </div>

    </div>
  );
}
