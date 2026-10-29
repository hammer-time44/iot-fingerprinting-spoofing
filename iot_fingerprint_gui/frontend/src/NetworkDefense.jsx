import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Shield, Activity, Play, Pause, RotateCcw,
  AlertTriangle, CheckCircle2, XCircle, Eye, Sliders, Terminal,
  Radio, Laptop, Skull, RefreshCw, Info, ArrowRight,
  TrendingDown, Check, ShieldAlert
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

const SCENARIO_LABELS = {
  IMPERSONATION: 'Fake Device (Stolen Identity)',
  UNKNOWN_HARDWARE: 'Unregistered Device',
  TIMING_MIMICRY: 'Timing Copycat',
  HIJACKED_DEVICE: 'Infected Device (Malware)',
  REPLAY: 'Recorded Traffic Playback',
  ACCESS_ATTEMPT: 'Outside Internet Hacker',
  BASELINE: 'Normal Traffic (No Attack)'
};

function formatDeviceName(raw) {
  if (!raw) return '';
  const specialMap = {
    AmazonEcho: 'Amazon Echo',
    BelkinWemoMotionSensor: 'Belkin WeMo Motion',
    PhilipsHue: 'Philips Hue',
    SamsungCamera: 'Samsung Camera',
    TPLinkSmartPlug: 'TP-Link Smart Plug'
  };
  if (specialMap[raw]) return specialMap[raw];
  return raw
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
    .trim();
}

export default function NetworkDefense({ globalThreshold = 0.84 }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Simplified two-input state
  const [attackerDevice, setAttackerDevice] = useState('SamsungCamera');
  const [pretendsToBe, setPretendsToBe] = useState('AmazonEcho');

  // Advanced settings state (collapsed by default)
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
  const [manualScenarioOverride, setManualScenarioOverride] = useState(null);
  const [simSpeed, setSimSpeed] = useState(1.0);
  const [tau, setTau] = useState(globalThreshold);
  const [scenarioParams, setScenarioParams] = useState({
    source_device: 'SamsungCamera',
    claimed_device: 'AmazonEcho',
    unseen_device: 'WithingsSmartScale',
    strength: 0.6,
    hijack_at_tick: 5,
    hijack_device: 'SamsungCamera'
  });

  // Simulation execution state
  const [simRunning, setSimRunning] = useState(false);
  const [simTick, setSimTick] = useState(0);
  const [hosts, setHosts] = useState({});
  const [events, setEvents] = useState([]);
  const [selectedHostId, setSelectedHostId] = useState('host-echo');
  const [ruleFormat, setRuleFormat] = useState('iptables'); // 'iptables' | 'nftables'

  const simRef = useRef(null);

  const classes = data?.meta?.classes || ['AmazonEcho', 'BelkinWemoMotionSensor', 'PhilipsHue', 'SamsungCamera', 'TPLinkSmartPlug'];
  const unseenList = data?.unseen ? Object.keys(data.unseen) : [];
  const benchmark = data?.benchmark || {};

  // Inferred scenario mapping
  const inferredScenario = useMemo(() => {
    if (manualScenarioOverride) return manualScenarioOverride;
    const isRegistered = classes.includes(attackerDevice);
    if (!isRegistered) {
      return 'UNKNOWN_HARDWARE';
    }
    if (attackerDevice === pretendsToBe) {
      return 'GENUINE_CONTROL';
    }
    return 'IMPERSONATION';
  }, [attackerDevice, pretendsToBe, classes, manualScenarioOverride]);

  // Live one-line plain-English sentence
  const helperSentence = useMemo(() => {
    if (manualScenarioOverride && manualScenarioOverride !== 'IMPERSONATION' && manualScenarioOverride !== 'UNKNOWN_HARDWARE' && manualScenarioOverride !== 'GENUINE_CONTROL') {
      const titles = {
        TIMING_MIMICRY: `Timing Copycat: ${formatDeviceName(attackerDevice)} mimics packet timing of ${formatDeviceName(pretendsToBe)} (strength ${(scenarioParams.strength || 0.6).toFixed(1)}).`,
        HIJACKED_DEVICE: `Infected Device (Compromised Device): ${formatDeviceName(pretendsToBe)} starts authentic, then transitions to compromised traffic at tick ${scenarioParams.hijack_at_tick || 5}.`,
        REPLAY: `Recorded Traffic Playback: Replaying previously recorded legitimate traffic of ${formatDeviceName(pretendsToBe)}.`,
        ACCESS_ATTEMPT: `Outside Internet Hacker: Remote scanner probes LAN ports; blocked at gateway firewall.`
      };
      return titles[manualScenarioOverride] || `Advanced scenario: ${manualScenarioOverride}`;
    }

    if (attackerDevice === pretendsToBe) {
      return `${formatDeviceName(attackerDevice)} is genuine and claims its own identity.`;
    }
    return `${formatDeviceName(attackerDevice)} will pretend to be ${formatDeviceName(pretendsToBe)}.`;
  }, [attackerDevice, pretendsToBe, manualScenarioOverride, scenarioParams]);

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

  // Sync tau
  useEffect(() => {
    if (simRef.current) {
      simRef.current.setTau(tau);
    }
  }, [tau]);

  // Handle simulation actions
  const handleStart = () => {
    if (!simRef.current) return;

    let params = { ...scenarioParams };
    const isRegistered = classes.includes(attackerDevice);

    if (inferredScenario === 'UNKNOWN_HARDWARE') {
      params = { ...params, unseen_device: attackerDevice, claimed_device: pretendsToBe };
    } else if (inferredScenario === 'GENUINE_CONTROL') {
      params = { ...params, source_device: attackerDevice, claimed_device: attackerDevice };
    } else if (inferredScenario === 'IMPERSONATION') {
      params = { ...params, source_device: attackerDevice, claimed_device: pretendsToBe };
    }

    simRef.current.setScenario(inferredScenario, params);
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
  const attackerHost = hosts['host-attacker-1'];
  const monitoredHost = attackerHost || selectedHost;

  // Derive Result Card state
  const resultCardData = useMemo(() => {
    if (!monitoredHost || (simTick === 0 && !simRunning)) {
      return {
        status: 'ready',
        headline: 'Ready to test',
        detail: 'Choose an attacking device and claimed identity, then click Start attack.',
        badge: 'IDLE',
        badgeClass: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-300 dark:border-slate-700',
        windowCount: 0
      };
    }

    const windowCount = monitoredHost.window_count || 0;

    if (windowCount < 5) {
      return {
        status: 'watching',
        headline: `Watching... (${windowCount} of 5 windows)`,
        detail: 'Accumulating 128-packet timing windows for multi-window device verdict.',
        badge: 'OBSERVING',
        badgeClass: 'bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-300 dark:border-slate-700',
        windowCount
      };
    }

    const verdict = monitoredHost.device_level_verdict;
    const isGenuine = attackerDevice === pretendsToBe && classes.includes(attackerDevice);

    if (verdict === 'SPOOF_SUSPECTED') {
      return {
        status: 'spoof',
        headline: 'Attack detected: this device is not who it claims to be',
        detail: `Technical verdict: SPOOF_SUSPECTED · Action: QUARANTINE · Detected after ${windowCount} windows.`,
        badge: 'QUARANTINED',
        badgeClass: 'bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200 border-amber-300 dark:border-amber-800',
        windowCount
      };
    }

    if (verdict === 'UNKNOWN_HARDWARE') {
      return {
        status: 'unknown',
        headline: 'Unknown device detected: it does not match any registered device',
        detail: `Technical verdict: UNKNOWN_HARDWARE · Action: ISOLATE · Detected after ${windowCount} windows.`,
        badge: 'ISOLATED',
        badgeClass: 'bg-rose-100 text-rose-900 dark:bg-rose-950 dark:text-rose-200 border-rose-300 dark:border-rose-800',
        windowCount
      };
    }

    if (verdict === 'VERIFIED') {
      if (isGenuine) {
        return {
          status: 'genuine',
          headline: 'Genuine device confirmed',
          detail: `Technical verdict: VERIFIED · Action: ALLOW · Confirmed after ${windowCount} windows.`,
          badge: 'TRUSTED',
          badgeClass: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200 border-emerald-300 dark:border-emerald-800',
          windowCount
        };
      }
      return {
        status: 'evaded',
        headline: 'Not detected: the traffic looks like the claimed device',
        detail: `Technical verdict: VERIFIED · Action: ALLOW · Observed ${windowCount} windows. Timing alone can sometimes be imitated.`,
        badge: 'TRUSTED',
        badgeClass: 'bg-indigo-100 text-indigo-900 dark:bg-indigo-950 dark:text-indigo-200 border-indigo-300 dark:border-indigo-800',
        windowCount
      };
    }

    return {
      status: 'evaluating',
      headline: `Evaluating traffic... (${windowCount} windows)`,
      detail: `Current verdict: ${verdict || 'Awaiting consensus'}`,
      badge: verdict || 'EVALUATING',
      badgeClass: 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-300 dark:border-slate-700',
      windowCount
    };
  }, [monitoredHost, simTick, simRunning, attackerDevice, pretendsToBe, classes]);

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
      </div>

      <div className="space-y-6">
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
                    {inferredScenario === 'ACCESS_ATTEMPT' ? 'Remote Scanner' : 'Rogue Host'}
                  </text>
                  <text x="35" y="88" textAnchor="middle" fontSize="8" fill="#9f1239">
                    {inferredScenario === 'ACCESS_ATTEMPT' ? 'WAN: 198.51.100.42' : '192.168.1.200'}
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
                  { id: 'host-echo', name: 'Echo Dot', x: 480, y: 55 },
                  { id: 'host-wemo', name: 'WeMo Motion', x: 555, y: 110 },
                  { id: 'host-hue', name: 'Hue Bridge', x: 635, y: 55 },
                  { id: 'host-camera', name: 'SmartCam', x: 715, y: 110 },
                  { id: 'host-plug', name: 'Smart Plug', x: 795, y: 55 }
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

          {/* SIMPLIFIED TWO-INPUT ATTACK CONTROLS */}
          <div className="p-5 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3.5 items-end">
              {/* Input 1: Attacking device */}
              <div className="sm:col-span-1 lg:col-span-5 space-y-1.5">
                <label htmlFor="attacking-device" className="block text-xs font-bold text-gray-700 dark:text-gray-300">
                  Attacking device
                </label>
                <select
                  id="attacking-device"
                  value={attackerDevice}
                  onChange={(e) => {
                    setAttackerDevice(e.target.value);
                    setManualScenarioOverride(null);
                  }}
                  className="w-full px-3 py-2 text-xs sm:text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  <optgroup label="Registered devices (5)">
                    {classes.map((cls) => (
                      <option key={cls} value={cls}>{formatDeviceName(cls)}</option>
                    ))}
                  </optgroup>
                  {unseenList.length > 0 && (
                    <optgroup label={`Unknown devices (${unseenList.length})`}>
                      {unseenList.map((u) => (
                        <option key={u} value={u}>{formatDeviceName(u)}</option>
                      ))}
                    </optgroup>
                  )}
                </select>
              </div>

              {/* Input 2: Pretends to be */}
              <div className="sm:col-span-1 lg:col-span-4 space-y-1.5">
                <label htmlFor="pretends-to-be" className="block text-xs font-bold text-gray-700 dark:text-gray-300">
                  Pretends to be
                </label>
                <select
                  id="pretends-to-be"
                  value={pretendsToBe}
                  onChange={(e) => {
                    setPretendsToBe(e.target.value);
                    setManualScenarioOverride(null);
                  }}
                  className="w-full px-3 py-2 text-xs sm:text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  {classes.map((cls) => (
                    <option key={cls} value={cls}>{formatDeviceName(cls)}</option>
                  ))}
                </select>
              </div>

              {/* Action Buttons: Start attack & Reset */}
              <div className="col-span-1 sm:col-span-2 lg:col-span-3 flex items-center gap-2">
                {!simRunning ? (
                  <button
                    type="button"
                    onClick={handleStart}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs cursor-pointer transition-colors"
                  >
                    <Play className="w-4 h-4 fill-current" />
                    <span>Start attack</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handlePause}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs sm:text-sm font-bold bg-amber-600 hover:bg-amber-700 text-white shadow-xs cursor-pointer transition-colors"
                  >
                    <Pause className="w-4 h-4" />
                    <span>Pause</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={handleReset}
                  className="px-3 py-2 rounded-lg text-xs sm:text-sm font-bold border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors flex items-center justify-center"
                  title="Reset simulation"
                  aria-label="Reset simulation"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Live Helper Sentence */}
            <div className="text-xs text-gray-600 dark:text-gray-400 font-medium flex items-center gap-2 pt-1 border-t border-gray-100 dark:border-gray-800">
              <Info className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
              <span id="attacker-sentence">{helperSentence}</span>
            </div>

            {/* Collapsed Advanced Settings Accordion */}
            <details
              id="advanced-settings"
              className="pt-2 border-t border-gray-100 dark:border-gray-800 text-xs"
              open={isAdvancedOpen}
              onToggle={(e) => setIsAdvancedOpen(e.currentTarget.open)}
            >
              <summary
                id="advanced-settings-toggle"
                className="font-semibold text-gray-500 hover:text-gray-900 dark:hover:text-gray-200 cursor-pointer select-none flex items-center gap-1.5 py-1"
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>Advanced settings</span>
                <span className="text-[10px] text-gray-400 font-normal hidden sm:inline">
                  (override scenario, mimicry strength, speed, &tau; threshold)
                </span>
              </summary>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-3">
                {/* Manual Scenario Override */}
                <div>
                  <label className="block text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1">
                    Scenario Override:
                  </label>
                  <select
                    id="manual-scenario-select"
                    value={manualScenarioOverride || inferredScenario}
                    onChange={(e) => {
                      setManualScenarioOverride(e.target.value);
                      if (simRef.current) simRef.current.setScenario(e.target.value, scenarioParams);
                    }}
                    className="w-full px-2.5 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-medium"
                  >
                    <option value="IMPERSONATION">1. Fake Device (Stolen Identity)</option>
                    <option value="UNKNOWN_HARDWARE">2. Unregistered Device</option>
                    <option value="TIMING_MIMICRY">3. Timing Copycat</option>
                    <option value="HIJACKED_DEVICE">4. Infected Device (Malware)</option>
                    <option value="REPLAY">5. Recorded Traffic Playback</option>
                    <option value="ACCESS_ATTEMPT">6. Outside Internet Hacker</option>
                  </select>
                </div>

                {/* Mimicry Strength */}
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

                {/* Tau Threshold Slider */}
                <div>
                  <div className="flex justify-between text-[11px] font-semibold text-gray-600 dark:text-gray-400 mb-1">
                    <span>Threshold (&tau;):</span>
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
                        type="button"
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
            </details>
          </div>

          {/* PROMINENT SIMPLE RESULT CARD */}
          <div
            className={`p-4 sm:p-5 rounded-xl border transition-all shadow-xs ${
              resultCardData.status === 'spoof'
                ? 'bg-amber-50/70 dark:bg-amber-950/40 border-amber-300 dark:border-amber-800 text-amber-950 dark:text-amber-100'
                : resultCardData.status === 'unknown'
                ? 'bg-rose-50/70 dark:bg-rose-950/40 border-rose-300 dark:border-rose-800 text-rose-950 dark:text-rose-100'
                : resultCardData.status === 'genuine'
                ? 'bg-emerald-50/70 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-950 dark:text-emerald-100'
                : resultCardData.status === 'evaded'
                ? 'bg-indigo-50/70 dark:bg-indigo-950/40 border-indigo-300 dark:border-indigo-800 text-indigo-950 dark:text-indigo-100'
                : 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 text-gray-900 dark:text-gray-100'
            }`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  {resultCardData.status === 'spoof' && <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0" />}
                  {resultCardData.status === 'unknown' && <XCircle className="w-5 h-5 text-rose-600 shrink-0" />}
                  {resultCardData.status === 'genuine' && <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />}
                  {resultCardData.status === 'evaded' && <AlertTriangle className="w-5 h-5 text-indigo-600 shrink-0" />}
                  {resultCardData.status === 'watching' && <Activity className="w-5 h-5 text-indigo-600 animate-pulse shrink-0" />}
                  {resultCardData.status === 'ready' && <Shield className="w-5 h-5 text-slate-500 shrink-0" />}

                  <h3 className="text-sm sm:text-base font-bold tracking-tight">
                    {resultCardData.headline}
                  </h3>
                </div>

                <p className="text-xs text-gray-600 dark:text-gray-400 font-medium">
                  {resultCardData.detail}
                </p>
              </div>

              {/* Status Badge & Observation Progress */}
              <div className="flex items-center gap-2 self-start sm:self-center shrink-0">
                <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${resultCardData.badgeClass}`}>
                  {resultCardData.badge}
                </span>
                {simTick > 0 && (
                  <span className="text-[11px] font-mono text-gray-500 dark:text-gray-400">
                    Tick {simTick}
                  </span>
                )}
              </div>
            </div>

            {/* Watching Progress Bar */}
            {resultCardData.status === 'watching' && (
              <div className="mt-3 w-full bg-gray-200 dark:bg-gray-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="h-full bg-indigo-600 dark:bg-indigo-400 transition-all duration-300"
                  style={{ width: `${Math.min((resultCardData.windowCount / 5) * 100, 100)}%` }}
                />
              </div>
            )}
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
                            <span className="text-[9px] px-1 rounded bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300">TEST</span>
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
                        <span className="font-semibold">{formatDeviceName(h.claimed_device)}</span>
                      </div>

                      <div className="flex justify-between text-[11px]">
                        <span className="text-gray-500">Predicted (5-Win):</span>
                        <span className="font-semibold text-indigo-600 dark:text-indigo-400">
                          {formatDeviceName(h.predicted_device) || 'Evaluating...'}
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
                      type="button"
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
                    No state transitions yet. Start attack scenario above to observe gateway reactions.
                  </div>
                ) : (
                  events.map((ev, idx) => (
                    <div
                      key={idx}
                      className="p-2 rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/40 text-[11px] space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-gray-800 dark:text-gray-200">
                          {ev.host_name} ({formatDeviceName(ev.claimed_device)})
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
    </div>
  );
}
