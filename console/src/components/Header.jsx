import React from 'react';
import { TrendingUp, GitBranch, BookLock, Database, Power } from 'lucide-react';

const TABS = [
  { id: 'cohort',   label: 'Cohort Benchmark',          Icon: TrendingUp },
  { id: 'timeline', label: 'Case Lifecycle Rail',        Icon: GitBranch  },
  { id: 'policy',   label: 'Compliance Cage',            Icon: BookLock   },
  { id: 'security', label: 'Audit Ledger',               Icon: Database   },
];

export default function Header({
  activeTab,
  setActiveTab,
  killSwitchEngaged,
  onToggleKillSwitch,
  selectedMerchant = 'merch_ecommerce_01',
  onSelectMerchant,
}) {
  return (
    <header style={{
      position: 'sticky', top: 0, zIndex: 50,
      background: 'rgba(7,9,15,0.92)',
      backdropFilter: 'blur(20px) saturate(180%)',
      borderBottom: '1px solid rgba(255,255,255,0.06)',
      padding: '0 32px',
    }}>
      <div style={{ maxWidth: 1480, margin: '0 auto', height: 52, display: 'flex', alignItems: 'center', gap: 0 }}>
        
        {/* ── Logo ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginRight: 32 }}>
          <div style={{
            width: 30, height: 30,
            background: 'linear-gradient(135deg, #0B1428 0%, #0F1E42 100%)',
            border: '1px solid rgba(43,120,255,0.30)',
            borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 12px rgba(43,120,255,0.15)',
          }}>
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
              <path d="M8 1.5L2 4.5V9C2 12.31 4.69 15.24 8 16C11.31 15.24 14 12.31 14 9V4.5L8 1.5Z"
                stroke="#2B78FF" strokeWidth="1.2" strokeLinejoin="round" fill="rgba(43,120,255,0.08)"/>
              <path d="M5.5 8.5L7 10L10.5 6.5"
                stroke="#00D68F" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 7 }}>
              <span style={{
                fontFamily: 'Sora, sans-serif', fontWeight: 700,
                fontSize: 13, letterSpacing: '0.14em',
                color: '#E8ECF5', textTransform: 'uppercase',
              }}>Backstop</span>
              <span style={{
                fontFamily: 'IBM Plex Mono, monospace', fontSize: 9,
                letterSpacing: '0.1em', color: '#2B78FF',
                background: 'rgba(43,120,255,0.08)',
                border: '1px solid rgba(43,120,255,0.18)',
                borderRadius: 4, padding: '1px 6px', textTransform: 'uppercase',
              }}>v2.0</span>
            </div>
            <div style={{
              fontFamily: 'IBM Plex Mono, monospace', fontSize: 9.5,
              color: '#47566A', letterSpacing: '0.02em', lineHeight: 1.3,
              marginTop: 1,
            }}>
              Policy-Gated AI · Razorpay Core
            </div>
          </div>
        </div>

        {/* ── MID Selector ── */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '5px 10px', borderRadius: 7,
          background: 'rgba(11,14,23,0.8)',
          border: '1px solid rgba(255,255,255,0.07)',
          marginRight: 20,
        }}>
          <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 9, color: '#47566A', letterSpacing: '0.1em', textTransform: 'uppercase' }}>MID</span>
          <select
            value={selectedMerchant}
            onChange={(e) => onSelectMerchant && onSelectMerchant(e.target.value)}
            style={{
              background: 'transparent', border: 'none', outline: 'none',
              fontFamily: 'Sora, sans-serif', fontSize: 11, fontWeight: 600,
              color: '#2B78FF', cursor: 'pointer',
            }}
          >
            <option value="merch_ecommerce_01">Apex Retail (merch_ecommerce_01)</option>
            <option value="merch_saas_sub_02">CloudScale SaaS (merch_saas_sub_02)</option>
          </select>
        </div>

        {/* ── Nav Tabs ── */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1 }}>
          {TABS.map(({ id, label, Icon }) => {
            const active = activeTab === id;
            return (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '6px 13px', borderRadius: 6, border: 'none',
                  cursor: 'pointer', transition: 'all 0.12s ease',
                  fontFamily: 'Sora, sans-serif', fontSize: 11.5, fontWeight: active ? 600 : 500,
                  letterSpacing: '0.01em',
                  background: active ? 'rgba(43,120,255,0.12)' : 'transparent',
                  color: active ? '#6BA4FF' : '#47566A',
                  boxShadow: active ? 'inset 0 0 0 1px rgba(43,120,255,0.20)' : 'none',
                  position: 'relative',
                }}
              >
                <Icon size={12} strokeWidth={active ? 2.2 : 1.8} />
                {label}
                {active && (
                  <span style={{
                    position: 'absolute', bottom: -1, left: '20%', right: '20%',
                    height: 2, background: '#2B78FF', borderRadius: 1,
                    opacity: 0.7,
                  }} />
                )}
              </button>
            );
          })}
        </nav>

        {/* ── Status row ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginLeft: 16 }}>

          {/* Policy version badge */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '4px 10px', borderRadius: 6,
            background: 'rgba(11,14,23,0.8)', border: '1px solid rgba(255,255,255,0.07)',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00D68F', display: 'inline-block', animation: 'pulse 2s ease-out infinite', boxShadow: '0 0 0 0 rgba(0,214,143,0.35)' }} className="pulse-ring" />
            <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 10, color: '#47566A', letterSpacing: '0.08em' }}>Policy</span>
            <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 10, color: '#7D8FA8', fontWeight: 600, letterSpacing: '0.06em' }}>2026.09.01</span>
          </div>

          {/* Kill-switch button */}
          <button
            onClick={onToggleKillSwitch}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '5px 12px', borderRadius: 6, border: 'none', cursor: 'pointer',
              fontFamily: 'IBM Plex Mono, monospace', fontSize: 10, fontWeight: 600,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              transition: 'all 0.15s ease',
              background: killSwitchEngaged
                ? 'rgba(240,48,81,0.10)'
                : 'rgba(0,214,143,0.08)',
              color: killSwitchEngaged ? '#F03051' : '#00D68F',
              boxShadow: killSwitchEngaged
                ? 'inset 0 0 0 1px rgba(240,48,81,0.25)'
                : 'inset 0 0 0 1px rgba(0,214,143,0.20)',
            }}
          >
            <Power size={11} />
            {killSwitchEngaged ? 'Kill Switch On' : 'Agent Active'}
          </button>
        </div>
      </div>
    </header>
  );
}
