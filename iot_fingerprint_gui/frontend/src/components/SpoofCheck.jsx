import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  HelpCircle,
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  Activity,
  Sliders,
  Database,
  ArrowRight,
  TrendingDown,
  Info,
  Layers,
  Lock,
  Unlock
} from 'lucide-react';

const DEVICE_LABELS = {
  AmazonEcho: 'Amazon Echo',
  BelkinWemoMotionSensor: 'Belkin WeMo Motion',
  PhilipsHue: 'Philips Hue Bridge',
  SamsungCamera: 'Samsung SmartCam',
  TPLinkSmartPlug: 'TP-Link Smart Plug'
};

const VERDICT_CONFIG = {
  VERIFIED: {
    label: 'VERIFIED',
    badgeClass: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700',
    dotClass: 'bg-emerald-500',
    icon: ShieldCheck,
    description: 'Timing signature matches claimed registered profile with sufficient confidence.'
  },
  SPOOF_SUSPECTED: {
    label: 'SPOOF SUSPECTED',
    badgeClass: 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border-rose-300 dark:border-rose-700',
    dotClass: 'bg-rose-500',
    icon: ShieldAlert,
    description: 'High-confidence timing mismatch: traffic resembles a different known device.'
  },
  UNKNOWN_HARDWARE: {
    label: 'UNKNOWN HARDWARE',
    badgeClass: 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-300 dark:border-amber-700',
    dotClass: 'bg-amber-500',
    icon: HelpCircle,
    description: 'Confidence below threshold: traffic does not match known timing fingerprints.'
  },
  INSUFFICIENT_DATA: {
    label: 'INSUFFICIENT DATA',
    badgeClass: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border-gray-300 dark:border-gray-700',
    dotClass: 'bg-gray-400',
    icon: Info,
    description: 'Awaiting minimum observation windows for device-level decision.'
  }
};

export default function SpoofCheck({ globalThreshold = 0.84 }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Verification parameters
  const [claimed, setClaimed] = useState('AmazonEcho');
  const [srcCategory, setSrcCategory] = useState('known'); // 'known' | 'unknown' | 'mimic'
  const [srcDevice, setSrcDevice] = useState('BelkinWemoMotionSensor');
  const [mimicIdx, setMimicIdx] = useState(2); // default strength 0.4
  const [tau, setTau] = useState(globalThreshold);
  const [windowN, setWindowN] = useState(5);

  // Playback / Replay state
  const [pos, setPos] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(600); // ms per step

  // Active matrix metric tab: 'rejection' | 'spoof' | 'unknown' | 'bypass'
  const [matrixMetric, setMatrixMetric] = useState('rejection');

  const timerRef = useRef(null);

  // Load precomputed evaluation data
  useEffect(() => {
    setLoading(true);
    fetch('/data/spoof_results.json')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load spoof_results.json`);
        return res.json();
      })
      .then((d) => {
        setData(d);
        if (d.classes && d.classes.length > 0) {
          setClaimed(d.classes[0]);
          setSrcDevice(d.classes.length > 1 ? d.classes[1] : d.classes[0]);
        }
        if (d.tau) setTau(d.tau);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching spoof_results.json:', err);
        setError('Could not load spoof evaluation results. Please ensure `python src/spoof_eval.py` has been executed.');
        setLoading(false);
      });
  }, []);

  // Update tau when parent globalThreshold changes
  useEffect(() => {
    if (globalThreshold && !data) {
      setTau(globalThreshold);
    }
  }, [globalThreshold, data]);

  // Available source options depending on category
  const sourceOptions = useMemo(() => {
    if (!data) return [];
    if (srcCategory === 'known') {
      return data.classes || [];
    }
    if (srcCategory === 'unknown') {
      return Object.keys(data.replay?.unknown || {});
    }
    // Mimicry: source is another known device morphing toward claimed
    return (data.classes || []).filter((c) => c !== claimed);
  }, [data, srcCategory, claimed]);

  // Synchronize source device if options change
  useEffect(() => {
    if (sourceOptions.length > 0 && !sourceOptions.includes(srcDevice)) {
      setSrcDevice(sourceOptions[0]);
      setPos(0);
      setIsPlaying(false);
    }
  }, [sourceOptions, srcDevice]);

  // Extract windows for active scenario
  const currentWindows = useMemo(() => {
    if (!data || !srcDevice) return [];
    if (srcCategory === 'known') {
      return data.replay?.known?.[srcDevice] || [];
    }
    if (srcCategory === 'unknown') {
      return data.replay?.unknown?.[srcDevice] || [];
    }
    const pairKey = `${srcDevice}>${claimed}`;
    const strengthStr = String(data.mimicry?.strengths?.[mimicIdx] ?? '0.4');
    return data.replay?.mimic?.[pairKey]?.[strengthStr] || [];
  }, [data, srcCategory, srcDevice, claimed, mimicIdx]);

  // Handle Playback Loop
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        setPos((prev) => {
          if (prev >= currentWindows.length) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, speed);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, speed, currentWindows.length]);

  // Reset position when scenario parameters change
  const handleScenarioChange = (newClaimed, newCat, newSrc, newMimic) => {
    if (newClaimed !== undefined) setClaimed(newClaimed);
    if (newCat !== undefined) setSrcCategory(newCat);
    if (newSrc !== undefined) setSrcDevice(newSrc);
    if (newMimic !== undefined) setMimicIdx(newMimic);
    setPos(0);
    setIsPlaying(false);
  };

  // Evaluate window verdict live in JS
  const evaluateWindow = (probVec) => {
    if (!probVec || !data?.classes) return null;
    let maxIdx = 0;
    let maxProb = probVec[0];
    for (let i = 1; i < probVec.length; i++) {
      if (probVec[i] > maxProb) {
        maxProb = probVec[i];
        maxIdx = i;
      }
    }
    const predClass = data.classes[maxIdx];
    let verdict;
    if (maxProb < tau) {
      verdict = 'UNKNOWN_HARDWARE';
    } else if (predClass === claimed) {
      verdict = 'VERIFIED';
    } else {
      verdict = 'SPOOF_SUSPECTED';
    }
    return {
      verdict,
      predClass,
      confidence: maxProb,
      claimedProb: probVec[data.classes.indexOf(claimed)] || 0.0,
      anomalyScore: 1.0 - maxProb,
      probs: probVec
    };
  };

  // Evaluated window outcomes for currently replayed sequence
  const evaluatedWindows = useMemo(() => {
    return currentWindows.slice(0, pos).map((p) => evaluateWindow(p));
  }, [currentWindows, pos, claimed, tau, data]);

  // Last observed window
  const lastObs = evaluatedWindows.length > 0 ? evaluatedWindows[evaluatedWindows.length - 1] : null;

  // Multi-window aggregated decision (soft probability average of last N windows)
  const deviceLevelDecision = useMemo(() => {
    if (!data || evaluatedWindows.length < windowN) {
      return { verdict: 'INSUFFICIENT_DATA', needed: windowN, observed: evaluatedWindows.length };
    }
    const recentWindows = currentWindows.slice(Math.max(0, pos - windowN), pos);
    const avgProbs = data.classes.map((_, colIdx) => {
      const sum = recentWindows.reduce((acc, row) => acc + (row[colIdx] || 0), 0);
      return sum / recentWindows.length;
    });
    return {
      ...evaluateWindow(avgProbs),
      observed: windowN,
      needed: windowN
    };
  }, [evaluatedWindows.length, currentWindows, pos, windowN, data, claimed, tau]);

  // Window outcome counts
  const tally = useMemo(() => {
    const counts = { VERIFIED: 0, SPOOF_SUSPECTED: 0, UNKNOWN_HARDWARE: 0 };
    evaluatedWindows.forEach((w) => {
      if (w?.verdict && counts[w.verdict] !== undefined) {
        counts[w.verdict]++;
      }
    });
    return counts;
  }, [evaluatedWindows]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 space-y-4 shadow-sm">
        <Activity className="w-8 h-8 text-indigo-600 animate-spin" />
        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Loading spoofing evaluation metrics...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-rose-50 dark:bg-rose-950/40 rounded-xl border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-200 space-y-3">
        <div className="flex items-center space-x-2 font-bold text-base">
          <AlertTriangle className="w-5 h-5 text-rose-600" />
          <span>Evaluation Data Unavailable</span>
        </div>
        <p className="text-xs leading-relaxed">{error}</p>
        <div className="text-xs bg-rose-100 dark:bg-rose-900/60 p-3 rounded font-mono">
          python src/spoof_eval.py --tau {tau}
        </div>
      </div>
    );
  }

  const { summary_metrics, classes, impersonation, impersonation_breakdown, legit_breakdown, mimicry } = data;
  const isLegitScenario = srcCategory === 'known' && srcDevice === claimed;

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* ── Page Header & Scope Banner ────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-800 gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-indigo-100 dark:bg-indigo-900/50 rounded-lg text-indigo-600 dark:text-indigo-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                Claimed-Identity Verification & Spoofing Detection
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Evaluates whether observed IAT signatures match a registered claimed identity using Random Forest inference with validation-calibrated open-set thresholding.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 px-3 py-1.5 rounded-lg text-xs font-semibold text-indigo-700 dark:text-indigo-300 self-start md:self-auto">
          <Database className="w-3.5 h-3.5" />
          <span>Offline Benchmark &middot; Held-Out Test Windows</span>
        </div>
      </div>

      {/* ── 4 Key Benchmark Metric Cards ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm space-y-1">
          <div className="flex justify-between items-center text-xs font-medium text-gray-500 dark:text-gray-400">
            <span>Legitimate Verification Rate</span>
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400">
            {summary_metrics?.overall_legit_verified_rate != null
              ? `${(summary_metrics.overall_legit_verified_rate * 100).toFixed(1)}%`
              : 'N/A'}
          </div>
          <div className="text-[11px] text-gray-500 dark:text-gray-400">
            {summary_metrics?.overall_legit_false_reject_rate != null
              ? `False reject: ${(summary_metrics.overall_legit_false_reject_rate * 100).toFixed(1)}% (controlled to ~5% budget)`
              : 'False reject: N/A'}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm space-y-1">
          <div className="flex justify-between items-center text-xs font-medium text-gray-500 dark:text-gray-400">
            <span>Impersonation Caught</span>
            <ShieldAlert className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-extrabold text-rose-600 dark:text-rose-400">
            {summary_metrics?.overall_impersonation_rejection_rate != null
              ? `${(summary_metrics.overall_impersonation_rejection_rate * 100).toFixed(1)}%`
              : 'N/A'}
          </div>
          <div className="text-[11px] text-gray-500 dark:text-gray-400">
            Total rejections on closed-set impersonation pairs
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm space-y-1">
          <div className="flex justify-between items-center text-xs font-medium text-gray-500 dark:text-gray-400">
            <span>Direct Spoof Flagging</span>
            <AlertTriangle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-extrabold text-rose-600 dark:text-rose-400">
            {summary_metrics?.overall_impersonation_spoof_rate != null
              ? `${(summary_metrics.overall_impersonation_spoof_rate * 100).toFixed(1)}%`
              : 'N/A'}
          </div>
          <div className="text-[11px] text-gray-500 dark:text-gray-400">
            Persistent mismatches flagged directly as SPOOF_SUSPECTED
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm space-y-1">
          <div className="flex justify-between items-center text-xs font-medium text-gray-500 dark:text-gray-400">
            <span>Calibrated Min Confidence (&tau;)</span>
            <Sliders className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-extrabold text-indigo-600 dark:text-indigo-400 font-mono">
            {tau.toFixed(2)}
          </div>
          <div className="text-[11px] text-gray-500 dark:text-gray-400">
            95th percentile validation anomaly threshold
          </div>
        </div>
      </div>

      {/* ── Interactive Replay & Verification Studio ────────────────────────── */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-gray-200 dark:border-gray-800">
          <div>
            <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-600" />
              Live Verification & Replay Studio
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Simulate identity claims by streaming pre-recorded test windows through the live verification decision rule.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => { setPos(0); setIsPlaying(true); }}
              disabled={currentWindows.length === 0}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Restart & Play</span>
            </button>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              disabled={currentWindows.length === 0 || pos >= currentWindows.length}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                isPlaying
                  ? 'bg-amber-600 hover:bg-amber-700 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200'
              } disabled:opacity-50`}
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              <span>{isPlaying ? 'Pause' : 'Play'}</span>
            </button>
            <button
              onClick={() => { setIsPlaying(false); setPos((p) => Math.min(p + 1, currentWindows.length)); }}
              disabled={currentWindows.length === 0 || pos >= currentWindows.length}
              className="p-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-xs transition-colors disabled:opacity-50"
              title="Step forward 1 window"
            >
              <SkipForward className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* ── Control Bar ──────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4 bg-gray-50 dark:bg-gray-800/40 rounded-xl border border-gray-200 dark:border-gray-800 text-xs">
          {/* Claimed Identity */}
          <div className="space-y-1.5">
            <label className="font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-indigo-500" />
              Claimed Registered Identity:
            </label>
            <select
              value={claimed}
              onChange={(e) => handleScenarioChange(e.target.value, undefined, undefined, undefined)}
              className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-indigo-500 font-medium"
            >
              {classes.map((cls) => (
                <option key={cls} value={cls}>
                  {DEVICE_LABELS[cls] || cls}
                </option>
              ))}
            </select>
          </div>

          {/* Traffic Category & Source */}
          <div className="space-y-1.5">
            <label className="font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
              <Unlock className="w-3.5 h-3.5 text-amber-500" />
              Observed Traffic Origin:
            </label>
            <div className="grid grid-cols-2 gap-1.5">
              <select
                value={srcCategory}
                onChange={(e) => handleScenarioChange(undefined, e.target.value, undefined, undefined)}
                className="bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1.5 text-xs text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-indigo-500 font-medium"
              >
                <option value="known">Known Device</option>
                <option value="unknown">Unseen Foreign</option>
                <option value="mimic">Morph Mimicry</option>
              </select>

              <select
                value={srcDevice}
                onChange={(e) => handleScenarioChange(undefined, undefined, e.target.value, undefined)}
                className="bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1.5 text-xs text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-indigo-500 font-medium truncate"
              >
                {sourceOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {DEVICE_LABELS[opt] || opt}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Mimicry slider or scenario badge */}
          <div className="space-y-1.5">
            {srcCategory === 'mimic' ? (
              <>
                <div className="flex justify-between items-center font-semibold text-gray-700 dark:text-gray-300">
                  <span>Imitation Morph Strength:</span>
                  <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">
                    {mimicry?.strengths?.[mimicIdx]}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max={(mimicry?.strengths?.length || 6) - 1}
                  step="1"
                  value={mimicIdx}
                  onChange={(e) => handleScenarioChange(undefined, undefined, undefined, parseInt(e.target.value, 10))}
                  className="w-full accent-indigo-600 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-lg cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-gray-400">
                  <span>0.0 (Pure Attacker)</span>
                  <span>1.0 (Target Quantiles)</span>
                </div>
              </>
            ) : (
              <>
                <label className="font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-emerald-500" />
                  Scenario Classification:
                </label>
                <div className="pt-1">
                  {isLegitScenario ? (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                      Legitimate Traffic Baseline
                    </span>
                  ) : srcCategory === 'known' ? (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-300 dark:border-rose-800">
                      Simulated Known Impersonator
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
                      Unseen Foreign Transmitter
                    </span>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Threshold & Window Size Controls */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center font-semibold text-gray-700 dark:text-gray-300">
              <span className="flex items-center gap-1">
                <Sliders className="w-3 h-3 text-indigo-500" />
                Confidence Threshold (&tau;):
              </span>
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">{tau.toFixed(2)}</span>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="range"
                min="0.50"
                max="0.99"
                step="0.01"
                value={tau}
                onChange={(e) => setTau(parseFloat(e.target.value))}
                className="w-full accent-indigo-600 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-lg cursor-pointer"
              />
              <button
                onClick={() => setTau(0.84)}
                title="Reset to validation-calibrated 0.84"
                className="px-1.5 py-0.5 text-[10px] bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 rounded text-gray-600 dark:text-gray-300"
              >
                0.84
              </button>
            </div>
            <div className="text-[10px] text-gray-400 flex justify-between">
              <span>0.50 (Loose)</span>
              <span>0.84 (Calibrated)</span>
              <span>0.99 (Strict)</span>
            </div>
          </div>
        </div>

        {/* Progress Timeline */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>Replay Progress: Window {pos} of {currentWindows.length}</span>
            <span>{currentWindows.length > 0 ? ((pos / currentWindows.length) * 100).toFixed(0) : 0}%</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-indigo-600 h-full transition-all duration-200 rounded-full"
              style={{ width: `${currentWindows.length > 0 ? (pos / currentWindows.length) * 100 : 0}%` }}
            />
          </div>
        </div>

        {/* ── Observation Cards: Current Window vs Device-Level ─────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
          {/* Current Window Observation */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800/40 rounded-xl border border-gray-200 dark:border-gray-800 space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700/60">
              <span className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                Current Observation (Window {pos > 0 ? pos : '–'})
              </span>
              {lastObs ? (
                <span className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-bold border ${VERDICT_CONFIG[lastObs.verdict].badgeClass}`}>
                  <span className={`w-2 h-2 rounded-full ${VERDICT_CONFIG[lastObs.verdict].dotClass}`} />
                  <span>{VERDICT_CONFIG[lastObs.verdict].label}</span>
                </span>
              ) : (
                <span className="text-xs text-gray-400">Waiting for stream...</span>
              )}
            </div>

            {lastObs ? (
              <div className="space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-2 p-2.5 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
                  <div>
                    <div className="text-gray-400 text-[11px]">Predicted Class:</div>
                    <div className="font-bold text-gray-900 dark:text-white text-sm">
                      {DEVICE_LABELS[lastObs.predClass] || lastObs.predClass}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-[11px]">Top Confidence:</div>
                    <div className="font-bold text-indigo-600 dark:text-indigo-400 text-sm font-mono">
                      {(lastObs.confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-[11px]">Claimed Identity:</div>
                    <div className="font-bold text-gray-700 dark:text-gray-300">
                      {DEVICE_LABELS[claimed] || claimed}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400 text-[11px]">Claimed Probability:</div>
                    <div className="font-bold font-mono text-gray-700 dark:text-gray-300">
                      {(lastObs.claimedProb * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>

                {/* Probability Distribution */}
                <div className="space-y-1.5 pt-1">
                  <div className="text-[11px] font-semibold text-gray-500 dark:text-gray-400">
                    Random Forest Probability Distribution:
                  </div>
                  {classes.map((cls, idx) => {
                    const prob = lastObs.probs[idx] || 0.0;
                    const isClaimed = cls === claimed;
                    const isTop = cls === lastObs.predClass;

                    return (
                      <div key={cls} className="space-y-0.5">
                        <div className="flex justify-between text-[11px]">
                          <span className={`flex items-center gap-1 ${isClaimed ? 'font-bold text-indigo-600 dark:text-indigo-400' : 'text-gray-600 dark:text-gray-400'}`}>
                            {DEVICE_LABELS[cls] || cls}
                            {isClaimed && <span className="text-[10px] bg-indigo-100 dark:bg-indigo-900/60 px-1 rounded text-indigo-700 dark:text-indigo-300">(Claimed)</span>}
                          </span>
                          <span className="font-mono text-gray-600 dark:text-gray-400">
                            {(prob * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-700 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              isTop
                                ? lastObs.verdict === 'VERIFIED'
                                  ? 'bg-emerald-500'
                                  : lastObs.verdict === 'SPOOF_SUSPECTED'
                                  ? 'bg-rose-500'
                                  : 'bg-amber-500'
                                : isClaimed
                                ? 'bg-indigo-400'
                                : 'bg-gray-300 dark:bg-gray-600'
                            }`}
                            style={{ width: `${Math.max(prob * 100, 1)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-gray-400">
                Click <b>Play</b> or <b>Restart & Play</b> above to stream windows through the detector.
              </div>
            )}
          </div>

          {/* Multi-Window Device-Level Analysis */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800/40 rounded-xl border border-gray-200 dark:border-gray-800 space-y-4 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700/60">
                <span className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                  Device-Level Aggregation (Last {windowN} Windows)
                </span>
                <span className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-bold border ${VERDICT_CONFIG[deviceLevelDecision.verdict].badgeClass}`}>
                  <span className={`w-2 h-2 rounded-full ${VERDICT_CONFIG[deviceLevelDecision.verdict].dotClass}`} />
                  <span>{VERDICT_CONFIG[deviceLevelDecision.verdict].label}</span>
                </span>
              </div>

              {/* Window Tally */}
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="p-2.5 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                  <div className="text-emerald-700 dark:text-emerald-300 font-extrabold text-lg">{tally.VERIFIED}</div>
                  <div className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">Verified</div>
                </div>
                <div className="p-2.5 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 rounded-lg">
                  <div className="text-rose-700 dark:text-rose-300 font-extrabold text-lg">{tally.SPOOF_SUSPECTED}</div>
                  <div className="text-[11px] text-rose-600 dark:text-rose-400 font-medium">Spoof Suspected</div>
                </div>
                <div className="p-2.5 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
                  <div className="text-amber-700 dark:text-amber-300 font-extrabold text-lg">{tally.UNKNOWN_HARDWARE}</div>
                  <div className="text-[11px] text-amber-600 dark:text-amber-400 font-medium">Unknown Hardware</div>
                </div>
              </div>

              {/* Rationale Callout */}
              <div className="p-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 text-xs space-y-1.5">
                <div className="font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-indigo-500" />
                  Decision Rationale:
                </div>
                <p className="text-gray-600 dark:text-gray-400 text-[11px] leading-relaxed">
                  {deviceLevelDecision.verdict === 'VERIFIED' && (
                    <>Observed traffic timing consistently matches <b>{DEVICE_LABELS[claimed] || claimed}</b> with averaged confidence &ge; {tau.toFixed(2)} across the observation window.</>
                  )}
                  {deviceLevelDecision.verdict === 'SPOOF_SUSPECTED' && (
                    <>Persistent timing mismatch detected: traffic consistently resembles <b>{DEVICE_LABELS[deviceLevelDecision.predClass] || deviceLevelDecision.predClass}</b> with high confidence ({(deviceLevelDecision.confidence * 100).toFixed(1)}%), contradicting the claimed identity <b>{DEVICE_LABELS[claimed] || claimed}</b>.</>
                  )}
                  {deviceLevelDecision.verdict === 'UNKNOWN_HARDWARE' && (
                    <>Traffic timing lacks sufficient affinity with any known signature (averaged confidence {(deviceLevelDecision.confidence * 100).toFixed(1)}% &lt; {tau.toFixed(2)}). Traffic is flagged as unregistered/unknown hardware.</>
                  )}
                  {deviceLevelDecision.verdict === 'INSUFFICIENT_DATA' && (
                    <>Awaiting {deviceLevelDecision.needed - deviceLevelDecision.observed} more observation window(s) to compute device-level aggregate confidence.</>
                  )}
                </p>
              </div>
            </div>

            <div className="text-[11px] text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700/60 pt-2 flex justify-between items-center">
              <span>Aggregation window size: <b>N = {windowN}</b> (640 packets)</span>
              <span className="font-medium text-indigo-600 dark:text-indigo-400">Soft Probability Averaging</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Complete Impersonation Matrix Table ──────────────────────────────── */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-200 dark:border-gray-800 gap-2">
          <div>
            <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-500" />
              Simulated Impersonation Evaluation Matrix (5 &times; 5)
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Evaluated across all 1,067 held-out test windows. Rows indicate the true transmitting hardware; columns indicate the claimed identity.
            </p>
          </div>

          {/* Metric Selector */}
          <div className="flex flex-wrap items-center gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg text-xs">
            <button
              onClick={() => setMatrixMetric('rejection')}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${matrixMetric === 'rejection' ? 'bg-white dark:bg-gray-700 text-indigo-600 dark:text-white shadow-xs' : 'text-gray-500'}`}
            >
              Total Rejection %
            </button>
            <button
              onClick={() => setMatrixMetric('spoof')}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${matrixMetric === 'spoof' ? 'bg-white dark:bg-gray-700 text-indigo-600 dark:text-white shadow-xs' : 'text-gray-500'}`}
            >
              Spoof Suspected %
            </button>
            <button
              onClick={() => setMatrixMetric('unknown')}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${matrixMetric === 'unknown' ? 'bg-white dark:bg-gray-700 text-indigo-600 dark:text-white shadow-xs' : 'text-gray-500'}`}
            >
              Unknown Hardware %
            </button>
            <button
              onClick={() => setMatrixMetric('bypass')}
              className={`px-2.5 py-1 rounded font-medium transition-colors ${matrixMetric === 'bypass' ? 'bg-white dark:bg-gray-700 text-indigo-600 dark:text-white shadow-xs' : 'text-gray-500'}`}
            >
              Bypass (False Verification) %
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
                <th className="py-2.5 px-3 font-semibold text-gray-700 dark:text-gray-300">
                  Actual Source Device (Test Split)
                </th>
                {classes.map((c) => (
                  <th key={c} className="py-2.5 px-3 text-center font-semibold text-gray-700 dark:text-gray-300">
                    Claims {DEVICE_LABELS[c] || c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {classes.map((src) => {
                const count = data.windows?.[src] || 0;
                return (
                  <tr key={src} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30">
                    <td className="py-2.5 px-3 font-medium text-gray-900 dark:text-gray-200">
                      {DEVICE_LABELS[src] || src}
                      <span className="text-[11px] text-gray-400 font-normal ml-1.5">(n={count})</span>
                    </td>
                    {classes.map((tgt) => {
                      const isDiag = src === tgt;
                      const b = impersonation_breakdown?.[src]?.[tgt];
                      const isBypass = matrixMetric === 'bypass';
                      let val = null;

                      if (matrixMetric === 'rejection') {
                        val = isDiag ? legit_breakdown?.[src]?.false_rejection_rate : b?.total_rejected_rate;
                      } else if (matrixMetric === 'spoof') {
                        val = isDiag ? legit_breakdown?.[src]?.misclassification_spoof_rate : b?.spoof_suspected_rate;
                      } else if (matrixMetric === 'unknown') {
                        val = isDiag ? legit_breakdown?.[src]?.low_confidence_unknown_rate : b?.unknown_hardware_rate;
                      } else if (isBypass) {
                        val = isDiag ? legit_breakdown?.[src]?.verified_rate : b?.verified_bypassed_rate;
                      }

                      const pct = val != null ? `${(val * 100).toFixed(1)}%` : 'N/A';

                      // Cell background and text color
                      let cellColor = '';
                      if (isBypass) {
                        // For bypass: on diagonal (legitimate), high verified is green; on off-diagonal (impersonation), 0% bypass is green, >0% is red!
                        cellColor = isDiag
                          ? 'bg-emerald-50 dark:bg-emerald-950/20 text-emerald-700 dark:text-emerald-400'
                          : (val || 0) > 0
                          ? 'bg-rose-50 dark:bg-rose-950/20 text-rose-700 dark:text-rose-400'
                          : 'bg-emerald-50/50 dark:bg-emerald-950/10 text-emerald-700 dark:text-emerald-400';
                      } else {
                        cellColor = isDiag
                          ? 'bg-emerald-50 dark:bg-emerald-950/20 text-emerald-700 dark:text-emerald-400'
                          : 'bg-rose-50/70 dark:bg-rose-950/20 text-rose-700 dark:text-rose-400';
                      }

                      return (
                        <td
                          key={tgt}
                          className={`py-2.5 px-3 text-center font-mono font-semibold ${cellColor}`}
                        >
                          {pct}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="flex flex-col sm:flex-row justify-between text-[11px] text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-100 dark:border-gray-800 gap-1">
          <div>
            <b>Green diagonal:</b> Legitimate traffic metric. <b>Red off-diagonal:</b> Simulated impersonator metric (Bypass % target: 0.0%).
          </div>
          <div>
            Model: <b>{data.model}</b> &middot; Threshold &tau; = {tau.toFixed(2)}
          </div>
        </div>
      </div>

      {/* ── Mimicry Degradation & Timing Disturbance Section ──────────────────── */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 shadow-sm space-y-4">
        <div>
          <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-indigo-600" />
            Detection Robustness vs. Timing Disturbances & Mimicry
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Evaluates how detection rates evolve when an adversary shapes inter-arrival times toward the target (Quantile Reshaping) or when network timing suffers Gaussian jitter.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
          {/* Quantile Reshaping */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800/40 rounded-xl border border-gray-200 dark:border-gray-800 space-y-3">
            <div className="text-xs font-bold text-gray-800 dark:text-gray-200">
              1. Quantile Morphing Toward Target Distribution
            </div>
            <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed">
              Adversary re-aligns empirical IAT quantiles with the claimed device profile. Intermediate values (0.2–0.6) distort timing and get caught as UNKNOWN_HARDWARE; high mimicry (&gt;0.8) begins to bypass class-level timing filters.
            </p>

            <div className="space-y-2 pt-2">
              {(mimicry?.strengths || [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]).map((s, idx) => {
                const rate = mimicry?.quantile?.avg?.[idx] || 0.0;
                return (
                  <div key={s} className="space-y-0.5 text-xs">
                    <div className="flex justify-between text-[11px]">
                      <span>Morph Strength <b>{s}</b></span>
                      <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">
                        {(rate * 100).toFixed(1)}% detected / rejected
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 h-2 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-600 dark:bg-indigo-500 rounded-full transition-all duration-300"
                        style={{ width: `${rate * 100}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Timing Jitter */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800/40 rounded-xl border border-gray-200 dark:border-gray-800 space-y-3">
            <div className="text-xs font-bold text-gray-800 dark:text-gray-200">
              2. Additive Network Timing Jitter (Log-Space Gaussian Noise)
            </div>
            <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed">
              Simulates real-world Wi-Fi bufferbloat and network congestion. As jitter increases, confidence drops below &tau; = {tau.toFixed(2)}, correctly triggering UNKNOWN_HARDWARE open-set rejections rather than false device attributions.
            </p>

            <div className="space-y-2 pt-2">
              {(mimicry?.strengths || [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]).map((s, idx) => {
                const rate = mimicry?.jitter?.avg?.[idx] || 0.0;
                return (
                  <div key={s} className="space-y-0.5 text-xs">
                    <div className="flex justify-between text-[11px]">
                      <span>Jitter Multiplier <b>&sigma; = {s}</b></span>
                      <span className="font-mono font-bold text-indigo-600 dark:text-indigo-400">
                        {(rate * 100).toFixed(1)}% rejected
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 h-2 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-600 dark:bg-indigo-500 rounded-full transition-all duration-300"
                        style={{ width: `${rate * 100}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>


    </div>
  );
}
