import React, { useState, useEffect, useRef } from 'react';
import {
  Shield, Activity, BarChart3, HelpCircle, Sun, Moon,
  AlertTriangle, RefreshCw, Radio, CheckCircle2, XCircle
} from 'lucide-react';
import LiveLabTab from './components/LiveLabTab';
import ScoreboardTab from './components/ScoreboardTab';
import HowItWorksTab from './components/HowItWorksTab';
import {
  checkBackendHealth, getModelInfo, getHosts, getBenchmarkResults,
  startSimulation, stopSimulation, resetSimulation, setSpeed, updateTau
} from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('livelab');
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('network_guard_theme');
    return saved ? saved === 'dark' : true;
  });

  const [backendStatus, setBackendStatus] = useState('checking');
  const [wsConnected, setWsConnected] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);
  const [unknownDevices, setUnknownDevices] = useState([]);

  // Simulation state
  const [hosts, setHosts] = useState({});
  const [tick, setTick] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [speed, setSpeedState] = useState(1.0);
  const [tau, setTau] = useState(0.84);
  const [activeScenario, setActiveScenario] = useState('BASELINE');
  const [events, setEvents] = useState([]);

  // Benchmark state
  const [benchmarkData, setBenchmarkData] = useState({});

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Sync dark mode class
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('network_guard_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('network_guard_theme', 'light');
    }
  }, [darkMode]);

  // Initial load
  useEffect(() => {
    let mounted = true;

    async function init() {
      try {
        const health = await checkBackendHealth();
        if (!mounted) return;
        if (health.status === 'ok') {
          setBackendStatus('online');
          setTau(health.tau || 0.84);
          setIsRunning(health.sim_running || false);
          setSpeedState(health.sim_speed || 1.0);
          setActiveScenario(health.scenario || 'BASELINE');
        } else {
          setBackendStatus('offline');
        }

        const info = await getModelInfo();
        if (mounted && info) {
          setModelInfo(info);
          if (info.unknown_devices_available) {
            setUnknownDevices(info.unknown_devices_available);
          }
        }

        const initialHosts = await getHosts();
        if (mounted && initialHosts && initialHosts.hosts) {
          setHosts(initialHosts.hosts);
        }

        const bData = await getBenchmarkResults();
        if (mounted && bData) {
          setBenchmarkData(bData);
        }
      } catch (err) {
        if (mounted) setBackendStatus('offline');
      }
    }

    init();
    return () => { mounted = false; };
  }, []);

  // WebSocket event stream
  useEffect(() => {
    let ws = null;
    let isCancelled = false;

    function connectWs() {
      if (isCancelled) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/events`;

      try {
        ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (isCancelled) return;
          setWsConnected(true);
          setBackendStatus('online');
        };

        ws.onmessage = (e) => {
          if (isCancelled) return;
          try {
            const data = JSON.parse(e.data);
            if (data.type === 'tick') {
              setTick(data.tick);
              if (data.hosts) setHosts(data.hosts);
              if (data.events && data.events.length > 0) {
                setEvents((prev) => [...data.events, ...prev].slice(0, 150));
              }
            } else if (data.type === 'status') {
              setIsRunning(data.running);
              setSpeedState(data.speed);
              setActiveScenario(data.scenario);
            }
          } catch (err) {
            console.error('Error parsing WS message:', err);
          }
        };

        ws.onclose = () => {
          if (isCancelled) return;
          setWsConnected(false);
          // Auto reconnect after 2 seconds
          reconnectTimeoutRef.current = setTimeout(connectWs, 2000);
        };

        ws.onerror = () => {
          if (isCancelled) return;
          setWsConnected(false);
        };
      } catch (err) {
        if (!isCancelled) {
          setWsConnected(false);
          reconnectTimeoutRef.current = setTimeout(connectWs, 3000);
        }
      }
    }

    connectWs();

    return () => {
      isCancelled = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (ws) ws.close();
    };
  }, []);

  // Periodic health check polling
  useEffect(() => {
    const interval = setInterval(async () => {
      const h = await checkBackendHealth();
      if (h.status === 'ok') {
        setBackendStatus('online');
      } else {
        setBackendStatus('offline');
        setWsConnected(false);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Handler functions
  const handleStartScenario = async (scenario, params) => {
    try {
      await startSimulation(scenario, params, speed);
      setIsRunning(true);
      setActiveScenario(scenario);
    } catch (err) {
      alert(`Start failed: ${err.message}`);
    }
  };

  const handleStopScenario = async () => {
    try {
      await stopSimulation();
      setIsRunning(false);
    } catch (err) {
      alert(`Stop failed: ${err.message}`);
    }
  };

  const handleResetScenario = async () => {
    try {
      await resetSimulation();
      setIsRunning(false);
      setTick(0);
      setEvents([]);
      const freshHosts = await getHosts();
      if (freshHosts.hosts) setHosts(freshHosts.hosts);
    } catch (err) {
      alert(`Reset failed: ${err.message}`);
    }
  };

  const handleSpeedChange = async (newSpeed) => {
    try {
      setSpeedState(newSpeed);
      await setSpeed(newSpeed);
    } catch (err) {
      console.error(err);
    }
  };

  const handleTauChange = async (newTau) => {
    try {
      setTau(newTau);
      await updateTau(newTau);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRefreshBenchmark = async () => {
    const data = await getBenchmarkResults();
    if (data) setBenchmarkData(data);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors">
      {/* Offline banner */}
      {backendStatus === 'offline' && (
        <div className="bg-rose-600 text-white px-4 py-2 text-xs font-semibold flex items-center justify-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          <span>Backend service offline or unreachable at port 8766. Please start the backend server via run.bat / run.sh.</span>
        </div>
      )}

      {/* Main Top Header */}
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            {/* Brand Logo & Title */}
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-indigo-600 text-white shadow-sm">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-sm sm:text-base font-extrabold tracking-tight">
                    Network Defense Lab
                  </h1>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 dark:bg-indigo-950/80 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 uppercase">
                    Simulated Gateway
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 hidden sm:block">
                  Encrypted IoT Device Fingerprinting via Traffic Timing Analysis
                </p>
              </div>
            </div>

            {/* Actions & Live Status */}
            <div className="flex items-center gap-3">
              {/* WS status badge */}
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
                <span className="text-[11px] font-mono text-slate-600 dark:text-slate-300">
                  {wsConnected ? 'LIVE FEED' : 'DISCONNECTED'}
                </span>
              </div>

              {/* Dark mode toggle */}
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-colors"
                title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              >
                {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
              </button>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex space-x-6 border-t border-slate-100 dark:border-slate-800/60 overflow-x-auto text-xs sm:text-sm font-semibold">
            <button
              onClick={() => setActiveTab('livelab')}
              className={`flex items-center gap-2 py-3 border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'livelab'
                  ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400 font-bold'
                  : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>Live Lab</span>
            </button>

            <button
              onClick={() => setActiveTab('scoreboard')}
              className={`flex items-center gap-2 py-3 border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'scoreboard'
                  ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400 font-bold'
                  : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span>Scoreboard & Benchmark</span>
            </button>

            <button
              onClick={() => setActiveTab('howitworks')}
              className={`flex items-center gap-2 py-3 border-b-2 transition-colors whitespace-nowrap ${
                activeTab === 'howitworks'
                  ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400 font-bold'
                  : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <HelpCircle className="w-4 h-4" />
              <span>How It Works & Limitations</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">
        {activeTab === 'livelab' && (
          <LiveLabTab
            hosts={hosts}
            tick={tick}
            isRunning={isRunning}
            speed={speed}
            tau={tau}
            activeScenario={activeScenario}
            events={events}
            unknownDevices={unknownDevices}
            onStartScenario={handleStartScenario}
            onStopScenario={handleStopScenario}
            onResetScenario={handleResetScenario}
            onSpeedChange={handleSpeedChange}
            onTauChange={handleTauChange}
          />
        )}

        {activeTab === 'scoreboard' && (
          <ScoreboardTab
            benchmarkData={benchmarkData}
            onRefreshBenchmark={handleRefreshBenchmark}
          />
        )}

        {activeTab === 'howitworks' && (
          <HowItWorksTab tau={tau} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 py-4 px-4 text-center text-xs text-slate-500 dark:text-slate-400">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700 dark:text-slate-300">Network Defense Lab</span>
            <span>&middot;</span>
            <span>Passive Gateway Defense Engine</span>
          </div>
          <div>
            Model: Random Forest (100 Trees) &middot; 13 Timing Moments &middot; Calibrated &tau; = {tau.toFixed(2)} &middot; Strict Zero Data Leakage
          </div>
        </div>
      </footer>
    </div>
  );
}
