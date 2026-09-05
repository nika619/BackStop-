import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import CohortScreen from './components/CohortScreen';
import TimelineScreen from './components/TimelineScreen';
import PolicyScreen from './components/PolicyScreen';
import SecurityScreen from './components/SecurityScreen';
import { Database, Download } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('cohort');
  const [benchmark, setBenchmark] = useState(null);
  const [cases, setCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [killSwitchEngaged, setKillSwitchEngaged] = useState(false);
  const [loadingBenchmark, setLoadingBenchmark] = useState(false);
  const [seeding, setSeeding] = useState(false);

  const fetchBenchmark = (recompute = false) => {
    setLoadingBenchmark(true);
    fetch(`http://127.0.0.1:8000/api/benchmark?recompute=${recompute}`)
      .then(r => r.json())
      .then(data => {
        setBenchmark(data);
        setLoadingBenchmark(false);
      })
      .catch(err => {
        console.error("Benchmark fetch error:", err);
        setLoadingBenchmark(false);
      });
  };

  const fetchCases = () => {
    fetch('http://127.0.0.1:8000/api/cases?limit=100')
      .then(r => r.json())
      .then(data => {
        setCases(data.cases || []);
      })
      .catch(err => console.error("Cases fetch error:", err));
  };

  const fetchKillSwitch = () => {
    fetch('http://127.0.0.1:8000/api/kill-switch')
      .then(r => r.json())
      .then(data => {
        setKillSwitchEngaged(data.kill_switch_engaged);
      })
      .catch(err => console.error("Kill switch fetch error:", err));
  };

  useEffect(() => {
    fetchBenchmark();
    fetchCases();
    fetchKillSwitch();
  }, []);

  const handleToggleKillSwitch = () => {
    const nextState = !killSwitchEngaged;
    fetch('http://127.0.0.1:8000/api/kill-switch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: !nextState, // enabled = true means agent runs
        actor: 'operator_ui',
        reason: nextState ? 'Operator engaged emergency stop' : 'Operator resumed agent',
      }),
    })
      .then(r => r.json())
      .then(data => {
        setKillSwitchEngaged(!data.agent_enabled);
      })
      .catch(err => console.error(err));
  };

  const handleSeedDemo = () => {
    setSeeding(true);
    fetch('http://127.0.0.1:8000/api/demo/seed?count=100', { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        setSeeding(false);
        fetchCases();
        fetchBenchmark(true);
      })
      .catch(err => {
        console.error(err);
        setSeeding(false);
      });
  };

  const handleProcessCase = (caseId) => {
    fetch(`http://127.0.0.1:8000/api/cases/${caseId}/process`, { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        fetchCases();
        fetchBenchmark(false);
      })
      .catch(err => console.error(err));
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-void)', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', fontFamily: 'var(--font-sans)' }}>
      
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        killSwitchEngaged={killSwitchEngaged}
        onToggleKillSwitch={handleToggleKillSwitch}
      />

      <main style={{ flex: 1, width: '100%', maxWidth: 1480, margin: '0 auto', padding: '20px 32px 40px' }}>
        
        {/* Seed notice — shown only when DB is empty */}
        {cases.length === 0 && (
          <div style={{
            marginBottom: 20, padding: '14px 20px',
            background: 'rgba(43,120,255,0.06)',
            border: '1px solid rgba(43,120,255,0.18)',
            borderRadius: 10,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Database size={15} color="rgba(43,120,255,0.7)" />
              <div>
                <p style={{ fontFamily: 'Sora, sans-serif', fontSize: 12, fontWeight: 600, color: 'rgba(255,255,255,0.65)' }}>No active cases in database</p>
                <p style={{ fontFamily: 'Sora, sans-serif', fontSize: 11, color: 'rgba(255,255,255,0.28)', marginTop: 2 }}>Seed 100 synthetic failed Razorpay payments to see live timelines and metrics.</p>
              </div>
            </div>
            <button onClick={handleSeedDemo} disabled={seeding} className="btn-primary">
              <Download size={12} style={{ animation: seeding ? 'bounce 1s ease infinite' : 'none' }} />
              {seeding ? 'Loading…' : 'Seed Sample Batch'}
            </button>
          </div>
        )}

        {activeTab === 'cohort' && (
          <CohortScreen benchmark={benchmark} onRefreshBenchmark={() => fetchBenchmark(true)} loading={loadingBenchmark} />
        )}
        {activeTab === 'timeline' && (
          <TimelineScreen cases={cases} selectedCaseId={selectedCaseId} onSelectCase={setSelectedCaseId} onProcessCase={handleProcessCase} />
        )}
        {activeTab === 'policy' && <PolicyScreen />}
        {activeTab === 'security' && (
          <SecurityScreen killSwitchEngaged={killSwitchEngaged} onToggleKillSwitch={handleToggleKillSwitch} />
        )}

      </main>

      <footer style={{
        borderTop: '1px solid rgba(255,255,255,0.04)',
        padding: '10px 32px',
        textAlign: 'center',
        fontFamily: 'IBM Plex Mono, monospace',
        fontSize: 9, letterSpacing: '0.12em',
        textTransform: 'uppercase',
        color: 'rgba(255,255,255,0.15)',
      }}>
        Backstop Revenue Recovery &nbsp;·&nbsp; Razorpay AI Buildathon 2026 &nbsp;·&nbsp; Track 03
      </footer>

    </div>
  );
}

