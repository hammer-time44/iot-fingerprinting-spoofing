import React, { useState } from 'react';
import {
  Shield, AlertTriangle, CheckCircle2, XCircle, Play, Pause, RotateCcw,
  Sliders, Terminal, Radio, Eye, Lock, Zap, ArrowRight, Activity,
  Server, Laptop, Skull, ExternalLink, RefreshCw
} from 'lucide-react';

export default function LiveLabTab({
  hosts = {},
  tick = 0,
  isRunning = false,
  speed = 1.0,
  tau = 0.84,
  activeScenario = 'BASELINE',
  events = [],
  unknownDevices = [],
  onStartScenario,
  onStopScenario,
  onResetScenario,
  onSpeedChange,
  onTauChange
}) {
  const [selectedScenario, setSelectedScenario] = useState('IMPERSONATION');
  const [scenarioParams, setScenarioParams] = useState({
    source_device: 'SamsungCamera',
    claimed_device: 'AmazonEcho',
    unseen_device: 'WithingsSmartScale',
    strength: 0.6,
    hijack_at_tick: 5,
    hijack_device: 'SamsungCamera'
  });
  const [selectedHostId, setSelectedHostId] = useState('host-echo');
  const [ruleFormat, setRuleFormat] = useState('iptables');

  const selectedHost = hosts[selectedHostId] || Object.values(hosts)[0];

  const handleStart = () => {
    onStartScenario(selectedScenario, scenarioParams);
  };

  const getStatusBadge = (state) => {
    switch (state) {
      case 'TRUSTED':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700"><CheckCircle2 className="w-3 h-3" /> TRUSTED (ALLOWED)</span>;
      case 'QUARANTINED':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300 border border-amber-300 dark:border-amber-700"><AlertTriangle className="w-3 h-3" /> QUARANTINED</span>;
      case 'ISOLATED':
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 dark:bg-rose-950/80 dark:text-rose-300 border border-rose-300 dark:border-rose-700"><XCircle className="w-3 h-3" /> ISOLATED (VLAN 99)</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border border-slate-300 dark:border-slate-700"><Eye className="w-3 h-3" /> OBSERVING</span>;
    }
  };

  const getVerdictColor = (verdict) => {
    switch (verdict) {
      case 'VERIFIED': return 'text-emerald-600 dark:text-emerald-400 font-bold';
      case 'SPOOF_SUSPECTED': return 'text-amber-600 dark:text-amber-400 font-bold';
      case 'UNKNOWN_HARDWARE': return 'text-rose-600 dark:text-rose-400 font-bold';
      default: return 'text-slate-500 font-medium';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Scenario Controller */}
      <div className="p-4 sm:p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-indigo-600 text-white"><Radio className="w-4 h-4" /></span>
              <h2 className="text-base sm:text-lg font-bold">Simulated Defense Operations Lab</h2>
              <span className="px-2 py-0.5 text-xs font-mono rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                Tick: #{tick}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Active Scenario: <span className="font-semibold text-indigo-600 dark:text-indigo-400">{activeScenario}</span> &middot; Replaying authentic UNSW encrypted timing windows with zero packet decryption.
            </p>
          </div>

          {/* Execution Controls */}
          <div className="flex flex-wrap items-center gap-2">
            {!isRunning ? (
              <button
                onClick={handleStart}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition shadow-sm cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" /> Run Scenario
              </button>
            ) : (
              <button
                onClick={onStopScenario}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition shadow-sm cursor-pointer"
              >
                <Pause className="w-3.5 h-3.5 fill-current" /> Pause
              </button>
            )}

            <button
              onClick={onResetScenario}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold transition cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Reset
            </button>

            {/* Speed Selector */}
            <div className="flex items-center gap-1.5 text-xs pl-2 border-l border-slate-200 dark:border-slate-800">
              <span className="text-slate-500 font-medium">Speed:</span>
              {[0.5, 1.0, 2.0, 4.0].map((s) => (
                <button
                  key={s}
                  onClick={() => onSpeedChange(s)}
                  className={`px-2 py-1 rounded text-[11px] font-bold ${
                    speed === s
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200'
                  }`}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Scenario Selection Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 mt-4 pt-1 text-xs">
          <div>
            <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1">Select Attack / Defense Scenario:</label>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 font-semibold"
            >
              <option value="BASELINE">1. Baseline Honest LAN (5 Devices)</option>
              <option value="IMPERSONATION">2. MAC Impersonation (Known X as Y)</option>
              <option value="UNKNOWN_HARDWARE">3. Unseen Foreign Hardware Injection</option>
              <option value="TIMING_MIMICRY">4. Timing Mimicry (Quantile Morphing)</option>
              <option value="HIJACKED_DEVICE">5. Compromised / Hijacked Device</option>
              <option value="REPLAY">6. Recorded Window Replay (Blind Spot)</option>
              <option value="ACCESS_ATTEMPT">7. Attacker WAN Access Attempt (Firewall Demo)</option>
            </select>
          </div>

          {/* Dynamic Scenario Parameters */}
          {selectedScenario === 'IMPERSONATION' && (
            <>
              <div>
                <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1">Attacker Physical Hardware (X):</label>
                <select
                  value={scenarioParams.source_device}
                  onChange={(e) => setScenarioParams({ ...scenarioParams, source_device: e.target.value })}
                  className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                >
                  <option value="SamsungCamera">SamsungCamera</option>
                  <option value="PhilipsHue">PhilipsHue</option>
                  <option value="BelkinWemoMotionSensor">BelkinWemoMotionSensor</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1">Claimed Identity Token (Y):</label>
                <select
                  value={scenarioParams.claimed_device}
                  onChange={(e) => setScenarioParams({ ...scenarioParams, claimed_device: e.target.value })}
                  className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
                >
                  <option value="AmazonEcho">AmazonEcho</option>
                  <option value="TPLinkSmartPlug">TPLinkSmartPlug</option>
                </select>
              </div>
            </>
          )}

          {selectedScenario === 'UNKNOWN_HARDWARE' && (
            <div>
              <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1">Unseen Device (UNSW Dataset):</label>
              <select
                value={scenarioParams.unseen_device}
                onChange={(e) => setScenarioParams({ ...scenarioParams, unseen_device: e.target.value })}
                className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
              >
                {unknownDevices.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          )}

          {selectedScenario === 'TIMING_MIMICRY' && (
            <div>
              <div className="flex justify-between font-semibold mb-1">
                <span>Morphing Strength (s):</span>
                <span className="text-indigo-600 dark:text-indigo-400">{scenarioParams.strength.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.1"
                value={scenarioParams.strength}
                onChange={(e) => setScenarioParams({ ...scenarioParams, strength: parseFloat(e.target.value) })}
                className="w-full accent-indigo-600"
              />
              <span className="text-[10px] text-slate-500">0.0 = Raw Camera &rarr; 1.0 = Quantile Echo</span>
            </div>
          )}

          {selectedScenario === 'HIJACKED_DEVICE' && (
            <div>
              <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1">Hijack at Tick:</label>
              <input
                type="number"
                min="2"
                max="10"
                value={scenarioParams.hijack_at_tick}
                onChange={(e) => setScenarioParams({ ...scenarioParams, hijack_at_tick: parseInt(e.target.value) || 5 })}
                className="w-full p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800"
              />
            </div>
          )}

          {/* Dynamic Tau Threshold Slider */}
          <div>
            <div className="flex justify-between font-semibold mb-1">
              <span>Threshold &tau; (Tau):</span>
              <span className="text-indigo-600 dark:text-indigo-400 font-mono font-bold">{tau.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.50"
              max="0.95"
              step="0.02"
              value={tau}
              onChange={(e) => onTauChange(parseFloat(e.target.value))}
              className="w-full accent-indigo-600 cursor-pointer"
            />
            <span className="text-[10px] text-slate-500">Validation 5th-percentile calibrated at 0.84</span>
          </div>
        </div>
      </div>

      {/* Interactive SVG Network Topology */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800 mb-4">
          <h3 className="text-sm font-bold flex items-center gap-2">
            <Server className="w-4 h-4 text-indigo-600" />
            Live Network Topology & Per-Host Security Status
          </h3>
          <span className="text-xs text-slate-500">Click any host below to inspect its timing moments & firewall rule</span>
        </div>

        {/* Visual SVG Bus / Router Diagram */}
        <div className="w-full overflow-x-auto py-2">
          <div className="min-w-[650px] flex items-center justify-between relative px-6 py-4 bg-slate-50/80 dark:bg-slate-950/60 rounded-xl border border-slate-200/80 dark:border-slate-800">
            {/* Attacker Subnet Node */}
            <div className="flex flex-col items-center z-10 w-36 text-center">
              <div className={`p-3 rounded-2xl border-2 transition ${
                hosts['host-attacker']
                  ? 'bg-rose-50 dark:bg-rose-950/40 border-rose-500 text-rose-600 animate-pulse'
                  : 'bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-400'
              }`}>
                <Skull className="w-7 h-7 mx-auto" />
              </div>
              <span className="text-xs font-bold mt-1 text-slate-800 dark:text-slate-200">Attacker Subnet</span>
              <span className="text-[10px] font-mono text-slate-500">10.0.0.0/24</span>
              {hosts['host-attacker'] && (
                <span className="mt-1 text-[10px] px-2 py-0.5 rounded font-bold bg-rose-600 text-white">
                  Active Threat
                </span>
              )}
            </div>

            {/* Connecting Pipe */}
            <div className="flex-1 h-1 bg-gradient-to-r from-rose-400 via-indigo-500 to-indigo-600 mx-2 relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded text-[9px] font-bold bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300 uppercase">
                WAN Uplink
              </div>
            </div>

            {/* Gateway Timing Monitor Node */}
            <div className="flex flex-col items-center z-10 w-48 text-center">
              <div className="p-3.5 rounded-2xl border-2 border-indigo-600 bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 shadow-lg shadow-indigo-500/10">
                <Shield className="w-8 h-8 mx-auto" />
              </div>
              <span className="text-xs font-bold mt-1 text-indigo-950 dark:text-indigo-200">Defense Gateway</span>
              <span className="text-[10px] font-mono text-slate-500">192.168.1.1 &middot; 13 Moments</span>
              <span className="mt-1 text-[10px] px-2 py-0.5 rounded font-mono font-semibold bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300">
                Tau Threshold = {tau.toFixed(2)}
              </span>
            </div>

            {/* Connecting Pipe */}
            <div className="flex-1 h-1 bg-gradient-to-r from-indigo-600 to-emerald-500 mx-2 relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded text-[9px] font-bold bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300 uppercase">
                Home LAN Bus
              </div>
            </div>

            {/* Protected LAN Cloud */}
            <div className="flex flex-col items-center z-10 w-36 text-center">
              <div className="p-3 rounded-2xl border-2 border-emerald-500 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600">
                <Laptop className="w-7 h-7 mx-auto" />
              </div>
              <span className="text-xs font-bold mt-1 text-slate-800 dark:text-slate-200">Registered LAN</span>
              <span className="text-[10px] font-mono text-slate-500">192.168.1.0/24</span>
              <span className="mt-1 text-[10px] px-2 py-0.5 rounded font-bold bg-emerald-600 text-white">
                5 Registered Devices
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Host Cards Grid */}
      <div>
        <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 mb-3 flex items-center gap-1.5">
          <Activity className="w-4 h-4 text-indigo-500" />
          Active Host Monitors & Probability Spectra
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.values(hosts).map((h) => {
            const isSelected = h.id === selectedHostId;
            const state = h.current_state || 'OBSERVING';

            let cardBorder = 'border-slate-200 dark:border-slate-800';
            if (state === 'TRUSTED') cardBorder = 'border-emerald-500 dark:border-emerald-600 ring-1 ring-emerald-500/20';
            if (state === 'QUARANTINED') cardBorder = 'border-amber-500 dark:border-amber-600 ring-1 ring-amber-500/20';
            if (state === 'ISOLATED') cardBorder = 'border-rose-500 dark:border-rose-600 ring-1 ring-rose-500/20';

            return (
              <div
                key={h.id}
                onClick={() => setSelectedHostId(h.id)}
                className={`p-4 rounded-xl border bg-white dark:bg-slate-900 transition cursor-pointer hover:shadow-md ${cardBorder} ${
                  isSelected ? 'shadow-md ring-2 ring-indigo-500' : ''
                }`}
              >
                {/* Header */}
                <div className="flex items-start justify-between gap-2 pb-2 border-b border-slate-100 dark:border-slate-800">
                  <div>
                    <h4 className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                      {h.is_attacker && <Skull className="w-3.5 h-3.5 text-rose-500" />}
                      {h.name}
                    </h4>
                    <span className="text-[10px] font-mono text-slate-500">{h.ip} &middot; {h.mac}</span>
                  </div>
                  <div>{getStatusBadge(state)}</div>
                </div>

                {/* Verdict & Prediction Breakdown */}
                <div className="grid grid-cols-2 gap-2 my-3 text-xs">
                  <div className="p-2 rounded bg-slate-50 dark:bg-slate-800/60">
                    <span className="block text-[10px] text-slate-500">Device-Level Verdict:</span>
                    <span className={`text-xs ${getVerdictColor(h.device_verdict)}`}>
                      {h.device_verdict || 'OBSERVING'}
                    </span>
                  </div>
                  <div className="p-2 rounded bg-slate-50 dark:bg-slate-800/60">
                    <span className="block text-[10px] text-slate-500">Model Confidence:</span>
                    <span className="text-xs font-mono font-bold">
                      {h.confidence ? `${(h.confidence * 100).toFixed(1)}%` : '0.0%'}
                    </span>
                  </div>
                </div>

                {/* Probability Distribution Bars */}
                <div className="space-y-1 mb-3">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Top Class Probabilities</span>
                  {Object.entries(h.probabilities || {})
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 3)
                    .map(([cls, prob]) => (
                      <div key={cls} className="space-y-0.5">
                        <div className="flex justify-between text-[10px]">
                          <span className="text-slate-600 dark:text-slate-400 truncate max-w-[150px]">{cls}</span>
                          <span className="font-mono text-slate-700 dark:text-slate-300">{(prob * 100).toFixed(0)}%</span>
                        </div>
                        <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-indigo-600 h-1.5 rounded-full transition-all duration-300"
                            style={{ width: `${Math.min(100, prob * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                </div>

                {/* Sparkline Visualizer */}
                {h.sparkline && h.sparkline.length > 1 && (
                  <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                    <div className="flex justify-between items-center text-[10px] text-slate-500 mb-1">
                      <span>Rolling Mean IAT (log1p):</span>
                      <span className="font-mono">{h.sparkline[h.sparkline.length - 1]}</span>
                    </div>
                    <svg className="w-full h-8 overflow-visible" viewBox="0 0 100 25" preserveAspectRatio="none">
                      <polyline
                        fill="none"
                        stroke="#6366f1"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        points={h.sparkline
                          .map((val, idx) => {
                            const x = (idx / (h.sparkline.length - 1)) * 100;
                            const minVal = Math.min(...h.sparkline);
                            const maxVal = Math.max(...h.sparkline) || 1;
                            const normY = maxVal === minVal ? 12.5 : 22 - ((val - minVal) / (maxVal - minVal)) * 19;
                            return `${x},${normY}`;
                          })
                          .join(' ')}
                      />
                    </svg>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Detail Inspector: Generated Firewall Rules & Recent Event Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Selected Host Firewall Rule */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800 mb-3">
              <h3 className="text-sm font-bold flex items-center gap-2">
                <Terminal className="w-4 h-4 text-indigo-600" />
                Generated Gateway Firewall Rule (Not Applied)
              </h3>
              <div className="flex rounded-lg bg-slate-100 dark:bg-slate-800 p-0.5 text-[11px] font-semibold">
                <button
                  onClick={() => setRuleFormat('iptables')}
                  className={`px-2.5 py-1 rounded-md transition ${ruleFormat === 'iptables' ? 'bg-indigo-600 text-white' : 'text-slate-600 dark:text-slate-400'}`}
                >
                  iptables
                </button>
                <button
                  onClick={() => setRuleFormat('nftables')}
                  className={`px-2.5 py-1 rounded-md transition ${ruleFormat === 'nftables' ? 'bg-indigo-600 text-white' : 'text-slate-600 dark:text-slate-400'}`}
                >
                  nftables
                </button>
              </div>
            </div>

            <p className="text-xs text-slate-500 mb-2">
              Action for <strong className="text-slate-900 dark:text-white">{selectedHost?.name || 'Selected Host'}</strong> ({selectedHost?.ip}):
            </p>

            <div className="p-3 bg-slate-950 text-emerald-400 font-mono text-xs rounded-lg overflow-x-auto leading-relaxed border border-slate-800">
              <pre className="whitespace-pre-wrap">
                {selectedHost?.firewall_rules?.[ruleFormat] || '# No rule generated for this host yet'}
              </pre>
            </div>
          </div>

          <div className="mt-4 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 text-[11px] text-slate-600 dark:text-slate-400">
            <strong>Simulation Guard Guarantee:</strong> Firewall commands are formatted as text for audit verification and are strictly never executed on physical network adapters.
          </div>
        </div>

        {/* Live Event Timeline */}
        <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800 mb-3">
            <h3 className="text-sm font-bold flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-600" />
              Live Security Event Stream
            </h3>
            <span className="text-xs text-slate-500">{events.length} events logged</span>
          </div>

          <div className="space-y-2 max-h-72 overflow-y-auto pr-1 text-xs">
            {events.length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                Waiting for simulation ticks. Start a scenario to stream timing events.
              </div>
            ) : (
              events.slice(-10).reverse().map((ev, i) => (
                <div key={i} className="p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 flex items-start justify-between gap-2">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-slate-400">{ev.timestamp}</span>
                      <strong className="text-slate-800 dark:text-slate-200">{ev.host_name || ev.host_id}</strong>
                      <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                        ev.action === 'ALLOW' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' :
                        ev.action === 'QUARANTINE' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300' :
                        'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                      }`}>
                        {ev.action}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-slate-400">
                      {ev.description || ev.rule_summary || `Verdict: ${ev.device_verdict} (conf: ${(ev.confidence * 100).toFixed(0)}%)`}
                    </p>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400 whitespace-nowrap">Tick #{ev.tick}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
