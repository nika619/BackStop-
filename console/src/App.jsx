import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import CohortScreen from './components/CohortScreen';
import TimelineScreen from './components/TimelineScreen';
import PolicyScreen from './components/PolicyScreen';
import SecurityScreen from './components/SecurityScreen';
import { RefreshCw, Database, Sparkles } from 'lucide-react';

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
    fetch(`http://localhost:8000/api/benchmark?recompute=${recompute}`)
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
    fetch('http://localhost:8000/api/cases?limit=100')
      .then(r => r.json())
      .then(data => {
        setCases(data.cases || []);
      })
      .catch(err => console.error("Cases fetch error:", err));
  };

  const fetchKillSwitch = () => {
    fetch('http://localhost:8000/api/kill-switch')
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
    fetch('http://localhost:8000/api/kill-switch', {
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
    fetch('http://localhost:8000/api/demo/seed?count=100', { method: 'POST' })
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
    fetch(`http://localhost:8000/api/cases/${caseId}/process`, { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        fetchCases();
        fetchBenchmark(false);
      })
      .catch(err => console.error(err));
  };

  return (
    <div className="min-h-screen bg-[#07090E] text-[#F3F5F9] flex flex-col font-sans">
      
      {/* Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        killSwitchEngaged={killSwitchEngaged}
        onToggleKillSwitch={handleToggleKillSwitch}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-6 space-y-6">
        
        {/* Quick Seeder bar if cases are empty */}
        {cases.length === 0 && (
          <div className="glass-panel p-4 bg-blue-950/20 border-blue-500/30 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Database className="w-5 h-5 text-blue-400" />
              <div>
                <h4 className="text-sm font-bold text-white">No active cases in database</h4>
                <p className="text-xs text-slate-400">Seed sample batch of 100 failed Razorpay payments to view live timelines and metrics.</p>
              </div>
            </div>
            <button
              onClick={handleSeedDemo}
              disabled={seeding}
              className="btn-primary text-xs"
            >
              <Sparkles className={`w-3.5 h-3.5 ${seeding ? 'animate-spin' : ''}`} />
              {seeding ? 'Seeding Database...' : 'Seed Sample Batch'}
            </button>
          </div>
        )}

        {/* Tab Views */}
        {activeTab === 'cohort' && (
          <CohortScreen
            benchmark={benchmark}
            onRefreshBenchmark={() => fetchBenchmark(true)}
            loading={loadingBenchmark}
          />
        )}

        {activeTab === 'timeline' && (
          <TimelineScreen
            cases={cases}
            selectedCaseId={selectedCaseId}
            onSelectCase={setSelectedCaseId}
            onProcessCase={handleProcessCase}
          />
        )}

        {activeTab === 'policy' && (
          <PolicyScreen />
        )}

        {activeTab === 'security' && (
          <SecurityScreen
            killSwitchEngaged={killSwitchEngaged}
            onToggleKillSwitch={handleToggleKillSwitch}
          />
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-[#1F2839] py-4 text-center text-xs text-slate-500 font-mono">
        BACKSTOP REVENUE RECOVERY • RAZORPAY AI BUILDATHON 2026 • TRACK 03
      </footer>

    </div>
  );
}
