import React from 'react';
import { TrendingUp, GitBranch, BookLock, ShieldOff, Power, Database } from 'lucide-react';

export default function Header({
  activeTab,
  setActiveTab,
  killSwitchEngaged,
  onToggleKillSwitch,
  selectedMerchant = "merch_ecommerce_01",
  onSelectMerchant,
}) {
  return (
    <header className="sticky top-0 z-50 bg-[#05070C]/95 backdrop-blur-md border-b border-[#1A2236] px-6 sm:px-8 py-3">
      <div className="max-w-[1500px] w-full mx-auto flex items-center justify-between">
        
        {/* Brand & Logo */}
        <div className="flex items-center gap-3.5">
          {/* Custom SVG logo — no emoji */}
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-[#0C1018] border border-[#263349] shadow-lg shadow-blue-900/20">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M10 2L3 5.5V10C3 13.87 6.06 17.48 10 18.5C13.94 17.48 17 13.87 17 10V5.5L10 2Z" stroke="#2F7EF5" strokeWidth="1.5" strokeLinejoin="round"/>
              <path d="M7 10L9 12L13 8" stroke="#00C48C" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-[15px] tracking-[0.08em] text-white uppercase" style={{fontFamily: 'Sora, sans-serif', letterSpacing: '0.12em'}}>
                Backstop
              </h1>
              <span className="text-[10px] px-2 py-0.5 rounded bg-[#0F1926] text-[#2F7EF5] border border-[#1A3060] font-mono tracking-widest uppercase">
                v2.0
              </span>
            </div>
            <p className="text-[10.5px] text-[#5A6B85] font-medium tracking-wide" style={{fontFamily: 'IBM Plex Mono, monospace'}}>
              Policy-Gated AI Revenue Recovery · Razorpay Core
            </p>
          </div>
        </div>

        {/* Multi-Tenant Merchant Selector */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0C1018] border border-[#1A2236]">
          <span className="text-[10px] text-[#5A6B85] font-mono uppercase tracking-widest">MID:</span>
          <select
            value={selectedMerchant}
            onChange={(e) => onSelectMerchant && onSelectMerchant(e.target.value)}
            className="bg-transparent text-[11px] text-[#2F7EF5] font-semibold px-1 py-0.5 outline-none cursor-pointer"
            style={{fontFamily: 'Sora, sans-serif'}}
          >
            <option value="merch_ecommerce_01">Apex Retail (merch_ecommerce_01)</option>
            <option value="merch_saas_sub_02">CloudScale SaaS (merch_saas_sub_02)</option>
          </select>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center bg-[#0C1018] p-1 rounded-xl border border-[#1A2236] gap-0.5">
          {[
            { id: 'cohort',   label: 'Cohort Benchmark',         Icon: TrendingUp },
            { id: 'timeline', label: 'Case Lifecycle Rail',       Icon: GitBranch  },
            { id: 'policy',   label: 'Compliance Cage (14 Rules)',Icon: BookLock   },
            { id: 'security', label: 'Audit Ledger & Kill Switch',Icon: Database   },
          ].map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`px-3.5 py-2 text-[11px] font-semibold rounded-lg flex items-center gap-1.5 transition-all ${
                activeTab === id
                  ? 'bg-[#0F1D40] text-[#2F7EF5] border border-[#1A3060]'
                  : 'text-[#5A6B85] hover:text-[#8A9BB5] hover:bg-[#111620]'
              }`}
              style={{fontFamily: 'Sora, sans-serif', letterSpacing: '0.01em'}}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </nav>

        {/* Status Indicators & Kill Switch Button */}
        <div className="flex items-center gap-3">
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0C1018] border border-[#1A2236] text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00C48C] animate-pulse"></span>
            <span className="text-[#5A6B85] font-mono">Policy:</span>
            <span className="font-mono text-[#8A9BB5] font-semibold tracking-widest">2026.09.01</span>
          </div>

          <button
            onClick={onToggleKillSwitch}
            className={`px-3 py-1.5 text-[11px] font-bold rounded-lg border flex items-center gap-1.5 transition-all tracking-widest uppercase ${
              killSwitchEngaged
                ? 'bg-red-950/80 text-red-300 border-red-800/60 hover:bg-red-900/80'
                : 'bg-[#04120A] text-[#00C48C] border-[#00C48C]/25 hover:bg-[#071A10]'
            }`}
            style={{fontFamily: 'IBM Plex Mono, monospace', fontSize: '10px'}}
          >
            <Power className="w-3 h-3" />
            {killSwitchEngaged ? 'Kill Switch On' : 'Agent Active'}
          </button>
        </div>

      </div>
    </header>
  );
}
