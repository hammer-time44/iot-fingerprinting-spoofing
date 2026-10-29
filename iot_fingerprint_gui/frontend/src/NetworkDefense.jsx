import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Shield, Activity, BarChart3, HelpCircle, Play, Pause, RotateCcw,
  AlertTriangle, CheckCircle2, XCircle, Eye, Lock, Sliders, Terminal,
  Radio, Zap, Laptop, Server, Skull, RefreshCw, Info, ArrowRight,
  TrendingDown, Database, ExternalLink
} from 'lucide-react';
import { ClientSimulation } from './networkDefense/simulation';

const VERDICT_BADGES = {
  TRUSTED: {
    label: 'TRUSTED (ALLOWED)',
    badgeClass: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700',
    dotClass: 'bg-emerald-500',
    icon: CheckCircle2
  },
  QUARANTINED: {
    label: 'QUARANTINED',
    badgeClass: 'bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300 border-amber-300 dark:border-amber-700',
    dotClass: 'bg-amber-500',
    icon: AlertTriangle
  },
  ISOLATED: {
    label: 'ISOLATED (VLAN 99)',
    badgeClass: 'bg-rose-100 text-rose-800 dark:bg-rose-950/80 dark:text-rose-300 border-rose-300 dark:border-rose-700',
    dotClass: 'bg-rose-500',
    icon: XCircle
  },
  OBSERVING: {
    label: 'OBSERVING',
    badgeClass: 'bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-300 dark:border-slate-700',
    dotClass: 'bg-slate-400',
    icon: Eye
  }
};

export default function NetworkDefense({ globalThreshold = 0.84 }) {
  const [activeSubTab, setActiveSubTab] = useState('livelab'); // 'livelab' | 'scoreboard' | 'howitworks'
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Simulation controls
  const [simRunning, setSimRunning] = useState(false);
  const [simTick, setSimTick] = useState(0);
  const [simSpeed, setSimSpeed] = useState(1.0);
  const [tau, setTau] = useState(globalThreshold);
  const [activeScenario, setActiveScenario] = useState('IMPERSONATION');
  const [scenarioParams, setScenarioParams] = useState({
    source_device: 'SamsungCamera',
    claimed_device: 'AmazonEcho',
    unseen_device: 'WithingsSmartScale',
    strength: 0.6,
    hijack_at_tick: 5,
    hijack_device: 'SamsungCamera'
  });

  // Live state
  const [hosts, setHosts] = useState({});
  const [events, setEvents] = useState([]);
  const [selectedHostId, setSelectedHostId] = useState('host-echo');
  const [ruleFormat, setRuleFormat] = useState('iptables'); // 'iptables' | 'nftables'

  const simRef = useRef(null);

  // Load static data
  useEffect(() => {
    setLoading(true);
    fetch('/data/network_guard_data.json')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load /data/network_guard_data.json`);
        return res.json();
      })
      .then((d) => {
        setData(d);
        if (d.meta?.tau) setTau(d.meta.tau);
        
        // Initialize client simulation engine
        const engine = new ClientSimulation(d, (tickResult) => {
          setSimTick(tickResult.tick);
          setHosts(tickResult.hosts);
          if (tickResult.events && tickResult.events.length > 0) {
            setEvents((prev) => [...tickResult.events, ...prev].slice(0, 100));
          }
        });
        simRef.current = engine;
        setHosts(engine.hosts);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error loading Network Defense data:', err);
        setError('Failed to load Network Defense simulation data. Please run `python network_guard/export_for_gui.py`.');
        setLoading(false);
      });

    return () => {
      if (simRef.current) simRef.current.stop();
    };
  }, []);

  // Update tau
  useEffect(() => {
    if (simRef.current) {
      simRef.current.setTau(tau);
    }
  }, [tau]);

  // Handle simulation actions
  const handleStart = () => {
    if (!simRef.current) return;
    simRef.current.setScenario(activeScenario, scenarioParams);
    simRef.current.setSpeed(simSpeed);
    simRef.current.start();
    setSimRunning(true);
  };

  const handlePause = () => {
    if (!simRef.current) return;
    simRef.current.stop();
    setSimRunning(false);
  };

  const handleReset = () => {
    if (!simRef.current) return;
    simRef.current.reset();
    setSimRunning(false);
    setSimTick(0);
    setEvents([]);
    setHosts(simRef.current.hosts);
  };

  const handleSpeedChange = (newSpeed) => {
    setSimSpeed(newSpeed);
    if (simRef.current) {
      simRef.current.setSpeed(newSpeed);
    }
  };

  const selectedHost = hosts[selectedHostId] || Object.values(hosts)[0];
  const classes = data?.meta?.classes || ['AmazonEcho', 'BelkinWemoMotionSensor', 'PhilipsHue', 'SamsungCamera', 'TPLinkSmartPlug'];
  const unseenList = data?.unseen ? Object.keys(data.unseen) : [];
  const benchmark = data?.benchmark || {};

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-slate-500 dark:text-slate-400 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
        <span className="text-sm font-semibold">Loading Network Defense Simulation Lab...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-xl border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-200 space-y-3">
        <div className="flex items-center gap-2 font-bold text-base">
          <AlertTriangle className="w-5 h-5 text-rose-600" />
          <span>Network Defense Lab Unavailable</span>
        </div>
        <p className="text-xs">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & Sub-Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-800 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-indigo-600 text-white shadow-sm">
              <Shield className="w-4 h-4" />
            </span>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">
              Network Defense Lab & Dynamic Policy Gateway
            </h2>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Gateway-level timing analysis: 13-feature Random Forest & 3-identity verification enforcing ALLOW / QUARANTINE / ISOLATE.
          </p>
        </div>

        {/* Sub-Tab Navigation Buttons */}
        <div className="flex items-center p-1 bg-gray-100 dark:bg-gray-800/80 rounded-lg border border-gray-200 dark:border-gray-700 text-xs font-semibold">
          <button
            onClick={() => setActiveSubTab('livelab')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
              activeSubTab === 'livelab'
                ? 'bg-white dark:bg-gray-900 text-indigo-600 dark:text-indigo-400 shadow-xs font-bold'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Live Lab</span>
          </button>

          <button
            onClick={() => setActiveSubTab('scoreboard')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
              activeSubTab === 'scoreboard'
                ? 'bg-white dark:bg-gray-900 text-indigo-600 dark:text-indigo-400 shadow-xs font-bold'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Scoreboard</span>
          </button>

          <button
            onClick={() => setActiveSubTab('howitworks')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all ${
              activeSubTab === 'howitworks'
                ? 'bg-white dark:bg-gray-900 text-indigo-600 dark:text-indigo-400 shadow-xs font-bold'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            <HelpCircle className="w-3.5 h-3.5" />
            <span>How It Works & Limits</span>
          </button>
        </div>
      </div>

      {/* SUB-TAB 1: LIVE LAB */}
      {activeSubTab === 'livelab' && (
        <div className="space-y-6">
          {/* Controls & Scenario Toolbar */}
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xs space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
                  Simulation Scenario Controls
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700">
                  Tick: {simTick}
                </span>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                {!simRunning ? (
                  <button
                    onClick={handleStart}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs cursor-pointer transition-colors"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>Start Scenario</span>
                  </button>
                ) : (
                  <button
                    onClick={handlePause}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-amber-600 hover:bg-amber-700 text-white shadow-xs cursor-pointer transition-colors"
                  >
                    <Pause className="w-3.5 h-3.5" />
                    <span>Pause</span>
                  </button>
                )}

                <button
                  onClick={handleReset}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Reset</span>
                </button>
              </div>
            </div>

            {/* Scenario Dropdown & Parameters */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              <div>
                <label className="block text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1">
                  Security Scenario:
                </label>
                <select
                  value={activeScenario}
                  onChange={(e) => {
                    setActiveScenario(e.target.value);
                    if (simRef.current) simRef.current.setScenario(e.target.value, scenarioParams);
                  }}
                  className="w-full px-2.5 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-medium"
                >
                  <option value="IMPERSONATION">1. Impersonation (Known Rogue)</option>
                  <option value="UNKNOWN_HARDWARE">2. Unknown Hardware (Unseen IoT)</option>
                  <option value="TIMING_MIMICRY">3. Timing Mimicry (Quantile Mapping)</option>
                  <option value="HIJACKED_DEVICE">4. Compromised Device (Mid-Stream)</option>
                  <option value="REPLAY">5. Replay Attack (Known Blind Spot)</option>
                  <option value="ACCESS_ATTEMPT">6. External Probe (Firewall Demo)</option>
                </select>
              </div>

              {/* Dynamic Parameter 1 */}
              {activeScenario === 'IMPERSONATION' && (
                <>
                  <div>
                    <label className="block text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1">
                      Attacker Hardware:
                    </label>
                    <select
                      value={scenarioParams.source_device}
                      onChange={(e) => setScenarioParams({ ...scenarioParams, source_device: e.target.value })}
                      className="w-full px-2.5 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    >
                      {classes.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1">
                      Claimed Identity:
                    </label>
                    <select
                      value={scenarioParams.claimed_device}
                      onChange={(e) => setScenarioParams({ ...scenarioParams, claimed_device: e.target.value })}
                      className="w-full px-2.5 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    >
                      {classes.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {activeScenario === 'UNKNOWN_HARDWARE' && (
                <>
                  <div>
                    <label className="block text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1">
                      Unseen Foreign Device:
                    </label>
                    <select
                      value={scenarioParams.unseen_device}
                      onChange={(e) => setScenarioParams({ ...scenarioParams, unseen_device: e.target.value })}
                      className="w-full px-2.5 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    >
                      {unseenList.map((u) => (
                        <option key={u} value={u}>{u}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1">
                      Claimed Identity:
                    </label>
                    <select
                      value={scenarioParams.claimed_device}
                      onChange={(e) => setScenarioParams({ ...scenarioParams, claimed_device: e.target.value })}
                      className="w-full px-2.5 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    >
                      {classes.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {activeScenario === 'TIMING_MIMICRY' && (
                <div>
                  <div className="flex justify-between text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1">
                    <span>Quantile Strength (s):</span>
                    <span className="font-mono text-indigo-600 dark:text-indigo-400">
                      {(scenarioParams.strength || 0.6).toFixed(1)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="1.0"
                    step="0.2"
                    value={scenarioParams.strength || 0.6}
                    onChange={(e) => setScenarioParams({ ...scenarioParams, strength: parseFloat(e.target.value) })}
                    className="w-full accent-indigo-600 cursor-pointer"
                  />
                </div>
              )}

              {/* Tau Threshold Slider */}
              <div>
                <div className="flex justify-between text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1">
                  <span>Confidence Threshold (&tau;):</span>
                  <span className="font-mono text-indigo-600 dark:text-indigo-400">{tau.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.50"
                  max="0.95"
                  step="0.01"
                  value={tau}
                  onChange={(e) => setTau(parseFloat(e.target.value))}
                  className="w-full accent-indigo-600 cursor-pointer"
                />
              </div>

              {/* Speed Controller */}
              <div>
                <div className="flex justify-between text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1">
                  <span>Replay Speed:</span>
                  <span className="font-mono text-indigo-600 dark:text-indigo-400">{simSpeed}x</span>
                </div>
                <div className="flex gap-1.5">
                  {[0.5, 1.0, 2.0, 4.0].map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSpeedChange(s)}
                      className={`flex-1 py-1 rounded text-[11px] font-bold border transition-colors ${
                        simSpeed === s
                          ? 'bg-indigo-600 text-white border-indigo-600'
                          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300'
                      }`}
                    >
                      {s}x
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* SVG Topology Diagram */}
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xs space-y-2">
            <div className="flex items-center justify-between pb-2 border-b border-gray-100 dark:border-gray-800 text-xs font-bold text-gray-700 dark:text-gray-300">
              <span className="flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-indigo-600" />
                Network Topology & Segmented Gateways
              </span>
              <span className="text-[11px] font-normal text-gray-500">Live State Diagram</span>
            </div>

            <div className="w-full overflow-x-auto py-2">
              <svg viewBox="0 0 880 200" className="w-full min-w-[700px] h-48 select-none">
                <defs>
                  <linearGradient id="wanGrad" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.2" />
                    <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.05" />
                  </linearGradient>
                  <linearGradient id="lanGrad" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity="0.15" />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity="0.03" />
                  </linearGradient>
                </defs>

                {/* Subnet Background Boxes */}
                <rect x="20" y="25" width="220" height="150" rx="10" fill="url(#wanGrad)" stroke="#f43f5e" strokeDasharray="3 3" strokeWidth="1.5" />
                <text x="35" y="48" fill="#e11d48" fontSize="11" fontWeight="bold">ATTACKER ZONE (WAN / ROGUE)</text>

                <rect x="440" y="20" width="420" height="160" rx="10" fill="url(#lanGrad)" stroke="#6366f1" strokeDasharray="3 3" strokeWidth="1.5" />
                <text x="455" y="43" fill="#4f46e5" fontSize="11" fontWeight="bold">HOME IOT LAN (192.168.1.0/24)</text>

                {/* Connection lines */}
                <line x1="240" y1="100" x2="310" y2="100" stroke="#94a3b8" strokeWidth="2" strokeDasharray="4 4" />
                <line x1="390" y1="100" x2="440" y2="100" stroke="#6366f1" strokeWidth="2" />

                {/* Attacker Node */}
                <g transform="translate(60, 65)">
                  <circle cx="35" cy="35" r="26" fill="#fecdd3" stroke="#e11d48" strokeWidth="2" />
                  <Skull className="w-6 h-6 text-rose-600" x="23" y="23" />
                  <text x="35" y="75" textAnchor="middle" fontSize="10" fontWeight="bold" fill="#881337">
                    {activeScenario === 'ACCESS_ATTEMPT' ? 'Remote Scanner' : 'Rogue Attacker'}
                  </text>
                  <text x="35" y="88" textAnchor="middle" fontSize="8" fill="#9f1239">
                    {activeScenario === 'ACCESS_ATTEMPT' ? 'WAN: 198.51.100.42' : '192.168.1.200'}
                  </text>
                </g>

                {/* Central Gateway Defense Node */}
                <g transform="translate(310, 60)">
                  <rect x="0" y="0" width="80" height="80" rx="12" fill="#312e81" stroke="#6366f1" strokeWidth="2" />
                  <Shield className="w-8 h-8 text-indigo-300" x="24" y="16" />
                  <text x="40" y="58" textAnchor="middle" fontSize="10" fontWeight="bold" fill="#ffffff">GATEWAY</text>
                  <text x="40" y="70" textAnchor="middle" fontSize="8" fill="#c7d2fe">&tau; = {tau.toFixed(2)}</text>
                </g>

                {/* Home LAN Nodes (5 Devices) */}
                {[
                  { id: 'host-echo', name: 'Echo Dot', x: 480, y: 55, color: '#10b981' },
                  { id: 'host-wemo', name: 'WeMo Motion', x: 555, y: 110, color: '#10b981' },
                  { id: 'host-hue', name: 'Hue Bridge', x: 635, y: 55, color: '#10b981' },
                  { id: 'host-camera', name: 'SmartCam', x: 715, y: 110, color: '#10b981' },
                  { id: 'host-plug', name: 'Smart Plug', x: 795, y: 55, color: '#10b981' }
                ].map((node) => {
                  const h = hosts[node.id];
                  let stateColor = '#10b981';
                  if (h?.state === 'QUARANTINED') stateColor = '#f59e0b';
                  if (h?.state === 'ISOLATED') stateColor = '#f43f5e';
                  if (h?.state === 'OBSERVING') stateColor = '#64748b';

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${node.x}, ${node.y})`}
                      className="cursor-pointer"
                      onClick={() => setSelectedHostId(node.id)}
                    >
                      <circle cx="20" cy="20" r="18" fill="#f8fafc" stroke={stateColor} strokeWidth={selectedHostId === node.id ? 3 : 2} />
                      <circle cx="20" cy="20" r="6" fill={stateColor} />
                      <text x="20" y="47" textAnchor="middle" fontSize="9" fontWeight="bold" fill="#334155">{node.name}</text>
                      <text x="20" y="58" textAnchor="middle" fontSize="7" fill="#64748b">{h?.state || 'OBSERVE'}</text>
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>

          {/* Host Cards Grid */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-gray-700 dark:text-gray-300">
              <span className="flex items-center gap-1.5">
                <Laptop className="w-4 h-4 text-indigo-600" />
                Network Hosts & Timing Fingerprint Status ({Object.keys(hosts).length})
              </span>
              <span className="text-[11px] text-gray-500 font-normal">Click any card to inspect active firewall rules</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.values(hosts).map((h) => {
                const badge = VERDICT_BADGES[h.state] || VERDICT_BADGES.OBSERVING;
                const isSelected = selectedHostId === h.id;

                return (
                  <div
                    key={h.id}
                    onClick={() => setSelectedHostId(h.id)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'border-indigo-600 ring-2 ring-indigo-500/20 bg-indigo-50/20 dark:bg-indigo-950/20'
                        : 'border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-gray-300 dark:hover:border-gray-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <h4 className="text-xs font-bold text-gray-900 dark:text-white flex items-center gap-1.5">
                          {h.display_name}
                          {h.id.startsWith('host-attacker') && (
                            <span className="text-[9px] px-1 rounded bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300">ROGUE</span>
                          )}
                        </h4>
                        <p className="text-[10px] font-mono text-gray-500 dark:text-gray-400">
                          {h.ip} &middot; {h.mac}
                        </p>
                      </div>

                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${badge.badgeClass}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${badge.dotClass}`} />
                        {badge.label}
                      </span>
                    </div>

                    <div className="space-y-2 text-xs pt-2 border-t border-gray-100 dark:border-gray-800/80">
                      <div className="flex justify-between text-[11px]">
                        <span className="text-gray-500">Claimed:</span>
                        <span className="font-semibold">{h.claimed_device}</span>
                      </div>

                      <div className="flex justify-between text-[11px]">
                        <span className="text-gray-500">Predicted (5-Win):</span>
                        <span className="font-semibold text-indigo-600 dark:text-indigo-400">
                          {h.predicted_device || 'Evaluating...'}
                        </span>
                      </div>

                      {/* Confidence Meter */}
                      <div>
                        <div className="flex justify-between text-[10px] mb-0.5">
                          <span className="text-gray-500">Confidence:</span>
                          <span className="font-mono font-bold">{(h.confidence * 100).toFixed(1)}%</span>
                        </div>
                        <div className="w-full bg-gray-100 dark:bg-gray-800 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-300 ${
                              h.confidence >= tau ? 'bg-indigo-600' : 'bg-amber-500'
                            }`}
                            style={{ width: `${Math.min(h.confidence * 100, 100)}%` }}
                          />
                        </div>
                      </div>

                      {/* Sparkline visualization */}
                      <div>
                        <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                          <span>Live IAT Sparkline:</span>
                          <span className="font-mono">{h.sparkline[h.sparkline.length - 1]}s</span>
                        </div>
                        <div className="h-6 flex items-end gap-1 bg-gray-50 dark:bg-gray-800/50 p-1 rounded">
                          {h.sparkline.map((val, idx) => {
                            const barHeight = Math.min(Math.max((val / 4.0) * 100, 15), 100);
                            return (
                              <div
                                key={idx}
                                className="flex-1 bg-indigo-500 dark:bg-indigo-400 rounded-t-xs transition-all"
                                style={{ height: `${barHeight}%` }}
                                title={`IAT: ${val}s`}
                              />
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Inspection Drawer: Rules & Event Stream */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Generated Firewall Rules Box */}
            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-gray-100 dark:border-gray-800">
                <div className="flex items-center gap-1.5 text-xs font-bold text-gray-900 dark:text-white">
                  <Terminal className="w-4 h-4 text-indigo-600" />
                  <span>Synthesized Firewall Rules (Text Only - Not Applied)</span>
                </div>
                <div className="flex gap-1">
                  {['iptables', 'nftables'].map((fmt) => (
                    <button
                      key={fmt}
                      onClick={() => setRuleFormat(fmt)}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold border ${
                        ruleFormat === fmt
                          ? 'bg-indigo-600 text-white border-indigo-600'
                          : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                      }`}
                    >
                      {fmt}
                    </button>
                  ))}
                </div>
              </div>

              <div className="text-[11px] text-gray-600 dark:text-gray-400">
                Target: <span className="font-semibold text-gray-900 dark:text-white">{selectedHost?.display_name}</span> ({selectedHost?.ip})
                &middot; Policy Action: <span className="font-bold text-indigo-600 dark:text-indigo-400">{selectedHost?.action}</span>
              </div>

              <pre className="p-3 rounded-lg bg-gray-950 text-emerald-400 font-mono text-[11px] overflow-x-auto leading-relaxed border border-gray-800">
                {selectedHost?.firewall_rules?.[ruleFormat] || `# Awaiting host state evaluation`}
              </pre>
            </div>

            {/* Live Security Event Stream */}
            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-gray-100 dark:border-gray-800">
                <div className="flex items-center gap-1.5 text-xs font-bold text-gray-900 dark:text-white">
                  <Activity className="w-4 h-4 text-indigo-600" />
                  <span>Dynamic Transition Event Timeline</span>
                </div>
                <span className="text-[10px] font-mono text-gray-500">{events.length} events logged</span>
              </div>

              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {events.length === 0 ? (
                  <div className="text-center py-8 text-xs text-gray-500 dark:text-gray-400">
                    No state transitions yet. Start simulation scenario above to observe gateway reactions.
                  </div>
                ) : (
                  events.map((ev, idx) => (
                    <div
                      key={idx}
                      className="p-2 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/40 text-[11px] space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-gray-800 dark:text-gray-200">
                          {ev.host_name} ({ev.claimed_device})
                        </span>
                        <span className="text-[10px] font-mono text-gray-400">{ev.timestamp}</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs">
                        <span className="font-mono text-gray-500">{ev.previous_state}</span>
                        <ArrowRight className="w-3 h-3 text-indigo-500" />
                        <span className="font-bold text-indigo-600 dark:text-indigo-400">{ev.new_state}</span>
                        <span className="text-[10px] text-gray-500 font-mono">({ev.action})</span>
                      </div>
                      <p className="text-[10px] text-gray-600 dark:text-gray-400 truncate">{ev.rule}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 2: SCOREBOARD */}
      {activeSubTab === 'scoreboard' && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xs space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-gray-100 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-indigo-600" />
                <h3 className="text-sm font-bold text-gray-900 dark:text-white">
                  30-Trial Empirical Security Benchmark Results
                </h3>
              </div>
              <span className="text-[11px] font-mono text-gray-500">
                Calibrated &tau; = {benchmark.tau || 0.84} &middot; {benchmark.n_trials || 30} Trials / Scenario
              </span>
            </div>

            {/* Benchmark Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-800 text-gray-500">
                    <th className="py-2.5 px-3 font-semibold">Scenario</th>
                    <th className="py-2.5 px-3 font-semibold">Trials</th>
                    <th className="py-2.5 px-3 font-semibold">Detection Rate</th>
                    <th className="py-2.5 px-3 font-semibold">Windows-to-Detect</th>
                    <th className="py-2.5 px-3 font-semibold">False Alarm Rate</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800 font-medium">
                  {benchmark.summary && Object.entries(benchmark.summary).map(([key, s]) => (
                    <tr key={key} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/50">
                      <td className="py-2.5 px-3 font-bold text-gray-900 dark:text-white">{key}</td>
                      <td className="py-2.5 px-3 font-mono">{s.trials}</td>
                      <td className="py-2.5 px-3">
                        <span className={`inline-block px-2 py-0.5 rounded font-mono font-bold text-[11px] ${
                          s.detection_rate_pct >= 90
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                            : s.detection_rate_pct > 0
                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                            : 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                        }`}>
                          {s.detection_rate_pct.toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {s.mean_windows_to_detect ? `${s.mean_windows_to_detect.toFixed(1)} w` : 'N/A'}
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {s.false_alarm_rate_pct !== undefined ? `${s.false_alarm_rate_pct.toFixed(1)}%` : '0.0%'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Benchmark Charts (Plain SVG) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Detection Rate Bar Chart */}
            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xs space-y-3">
              <h4 className="text-xs font-bold text-gray-900 dark:text-white flex items-center gap-1.5">
                <BarChart3 className="w-3.5 h-3.5 text-indigo-600" />
                Detection Percentage by Attack Class
              </h4>

              <div className="space-y-2 pt-2 text-xs">
                {benchmark.summary && Object.entries(benchmark.summary).map(([key, s]) => (
                  <div key={key}>
                    <div className="flex justify-between text-[11px] mb-1">
                      <span className="font-semibold text-gray-700 dark:text-gray-300">{key}</span>
                      <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">
                        {s.detection_rate_pct.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 dark:bg-gray-800 h-2.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          s.detection_rate_pct >= 90
                            ? 'bg-emerald-500'
                            : s.detection_rate_pct > 0
                            ? 'bg-amber-500'
                            : 'bg-rose-500'
                        }`}
                        style={{ width: `${Math.max(s.detection_rate_pct, 2)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Mimicry Resistance Curve */}
            <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xs space-y-3">
              <h4 className="text-xs font-bold text-gray-900 dark:text-white flex items-center gap-1.5">
                <TrendingDown className="w-3.5 h-3.5 text-indigo-600" />
                Timing Mimicry Evasion Curve (Quantile Reshaping)
              </h4>

              <div className="w-full pt-2">
                <svg viewBox="0 0 400 160" className="w-full h-36">
                  {/* Grid lines */}
                  <line x1="40" y1="20" x2="380" y2="20" stroke="#94a3b8" strokeOpacity="0.2" />
                  <line x1="40" y1="70" x2="380" y2="70" stroke="#94a3b8" strokeOpacity="0.2" />
                  <line x1="40" y1="120" x2="380" y2="120" stroke="#94a3b8" strokeOpacity="0.2" />

                  {/* Axes */}
                  <line x1="40" y1="20" x2="40" y2="120" stroke="#64748b" strokeWidth="1" />
                  <line x1="40" y1="120" x2="380" y2="120" stroke="#64748b" strokeWidth="1" />

                  {/* Y Axis Labels */}
                  <text x="32" y="24" fontSize="9" textAnchor="end" fill="#64748b">100%</text>
                  <text x="32" y="74" fontSize="9" textAnchor="end" fill="#64748b">50%</text>
                  <text x="32" y="124" fontSize="9" textAnchor="end" fill="#64748b">0%</text>

                  {/* Points from mimicry_curve */}
                  {benchmark.mimicry_curve && (
                    <>
                      <polyline
                        fill="none"
                        stroke="#6366f1"
                        strokeWidth="2.5"
                        points={benchmark.mimicry_curve
                          .map((pt, idx) => {
                            const x = 50 + idx * 60;
                            const y = 120 - (pt.detection_rate_pct / 100) * 100;
                            return `${x},${y}`;
                          })
                          .join(' ')}
                      />
                      {benchmark.mimicry_curve.map((pt, idx) => {
                        const x = 50 + idx * 60;
                        const y = 120 - (pt.detection_rate_pct / 100) * 100;
                        return (
                          <g key={idx}>
                            <circle cx={x} cy={y} r="3.5" fill="#4f46e5" stroke="#ffffff" strokeWidth="1.5" />
                            <text x={x} y="136" fontSize="8" textAnchor="middle" fill="#64748b">
                              s={pt.strength}
                            </text>
                          </g>
                        );
                      })}
                    </>
                  )}
                </svg>
              </div>
              <p className="text-[10px] text-gray-500 dark:text-gray-400">
                Adversary achieves evasion when quantile mapping strength exceeds s &ge; 0.9.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 3: HOW IT WORKS & LIMITS */}
      {activeSubTab === 'howitworks' && (
        <div className="space-y-6">
          {/* 4-Stage Pipeline */}
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2 pb-2 border-b border-gray-100 dark:border-gray-800">
              <Activity className="w-4 h-4 text-indigo-600" />
              The 4-Stage Passive Gateway Pipeline
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30 space-y-1">
                <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase">Stage 1</span>
                <h4 className="font-bold text-gray-900 dark:text-white">Packet Grouping & IAT</h4>
                <p className="text-[11px] text-gray-600 dark:text-gray-400">
                  Packets are grouped by host (MAC / IP). Inter-arrival times are log-transformed via log1p(IAT).
                </p>
              </div>

              <div className="p-3 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30 space-y-1">
                <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase">Stage 2</span>
                <h4 className="font-bold text-gray-900 dark:text-white">13 Statistical Moments</h4>
                <p className="text-[11px] text-gray-600 dark:text-gray-400">
                  Each 128-packet window produces 13 moments: Mean, Std, Median, Min, Max, Skew, Kurtosis, P25, P75, P95, P99, Energy, Entropy.
                </p>
              </div>

              <div className="p-3 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30 space-y-1">
                <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase">Stage 3</span>
                <h4 className="font-bold text-gray-900 dark:text-white">Random Forest (100 Trees)</h4>
                <p className="text-[11px] text-gray-600 dark:text-gray-400">
                  Z-score normalized features are evaluated by the 100-tree ensemble to yield class probability vectors.
                </p>
              </div>

              <div className="p-3 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/30 space-y-1">
                <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase">Stage 4</span>
                <h4 className="font-bold text-gray-900 dark:text-white">3-Identity Verdict Engine</h4>
                <p className="text-[11px] text-gray-600 dark:text-gray-400">
                  Compares Predicted Identity with Claimed Identity and threshold &tau; ({tau.toFixed(2)}) over 5-window voting.
                </p>
              </div>
            </div>
          </div>

          {/* Honest Scientific Limits Box */}
          <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/40 shadow-xs space-y-3">
            <div className="flex items-center gap-2 font-bold text-gray-900 dark:text-white text-xs">
              <Info className="w-4 h-4 text-indigo-600" />
              Honest Scientific Limits & Academic Boundaries
            </div>

            <ul className="list-disc pl-5 space-y-1.5 text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
              <li>
                <strong>Closed Set of 5 Devices:</strong> The model was trained strictly on 5 registered IoT device classes. The 22 other devices in the UNSW benchmark are treated as foreign unknown hardware.
              </li>
              <li>
                <strong>Timing Can Be Imitated:</strong> With quantile mapping (s &ge; 0.9), an adversary who can introduce controlled packet delays can reshape timings to bypass detection.
              </li>
              <li>
                <strong>Replay Attack Blind Spot:</strong> An attacker capturing and replaying exact recorded test windows will PASS verification as TRUSTED. Timing analysis verifies behavior, not cryptographic freshness.
              </li>
              <li>
                <strong>LAN Threat Realism:</strong> Remote WAN attackers cannot forge internal Layer-2 MAC addresses across routers; the realistic threat modeled is a rogue or compromised device physically on the local LAN.
              </li>
              <li>
                <strong>Firewall Demo Distinction:</strong> The "External Access Attempt" scenario demonstrates the gateway's perimeter default-deny firewall policy, not a machine learning classification.
              </li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

