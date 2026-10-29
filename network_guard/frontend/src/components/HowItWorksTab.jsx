import React from 'react';
import {
  HelpCircle, Shield, ArrowRight, Activity, Terminal, AlertTriangle,
  Lock, CheckCircle2, XCircle, Info, RefreshCw
} from 'lucide-react';

export default function HowItWorksTab({ tau = 0.84 }) {
  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="p-1.5 rounded-lg bg-indigo-600 text-white"><HelpCircle className="w-4 h-4" /></span>
          <h2 className="text-base sm:text-lg font-bold">How Network Defense Lab Works: Plain-Language Architecture</h2>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          An educational walkthrough of passive encrypted traffic timing analysis, 3-identity verification, and autonomous response policies.
        </p>
      </div>

      {/* The 4-Stage Ingestion Pipeline */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <h3 className="text-sm font-bold flex items-center gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
          <Activity className="w-4 h-4 text-indigo-600" />
          The 4-Stage Passive Ingestion Pipeline
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
          <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/30 space-y-1.5">
            <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Stage 1</span>
            <h4 className="font-bold text-slate-900 dark:text-white">Delta-t (IAT) Extraction</h4>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              Only arrival timestamps ($t_i$) are inspected. Consecutive differences $\Delta t_i = t_i - t_{i-1}$ are logged and damped via $\log(1 + \Delta t)$. Payloads are completely ignored.
            </p>
          </div>

          <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/30 space-y-1.5">
            <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Stage 2</span>
            <h4 className="font-bold text-slate-900 dark:text-white">13 Timing Moments</h4>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              A 128-packet window is reduced to 13 statistical moments: Mean, Std, Median, Min, Max, Skewness, Kurtosis, P25, P75, P95, P99, Signal Energy, and Shannon Entropy.
            </p>
          </div>

          <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/30 space-y-1.5">
            <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Stage 3</span>
            <h4 className="font-bold text-slate-900 dark:text-white">Random Forest (100 Trees)</h4>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              Features are normalized with training z-scores. A 100-tree ensemble outputs class probabilities across the 5 known devices (P(Echo), P(Cam), etc.).
            </p>
          </div>

          <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/30 space-y-1.5">
            <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Stage 4</span>
            <h4 className="font-bold text-slate-900 dark:text-white">3-Identity Verdict Engine</h4>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              Compares Predicted Identity with Claimed Identity and threshold &tau; ({tau.toFixed(2)}). An n=5 window voting buffer eliminates noisy single-window fluctuations.
            </p>
          </div>
        </div>
      </div>

      {/* The 3-Identity Rule Matrix */}
      <div className="p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-3">
        <h3 className="text-sm font-bold flex items-center gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
          <Shield className="w-4 h-4 text-indigo-600" />
          The Three-Identity Verdict & Policy Matrix
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-4 rounded-xl border border-emerald-300 dark:border-emerald-700 bg-emerald-50/50 dark:bg-emerald-950/30 space-y-1.5">
            <div className="flex items-center gap-1.5 font-bold text-emerald-800 dark:text-emerald-300">
              <CheckCircle2 className="w-4 h-4" /> VERIFIED &rarr; ALLOW
            </div>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              <strong>Condition:</strong> Top Predicted == Claimed AND Confidence &ge; &tau;.
            </p>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              <strong>Action:</strong> Host transitions to <code>TRUSTED</code>. Forwarding rules generated to allow normal WAN/LAN traffic.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-amber-300 dark:border-amber-700 bg-amber-50/50 dark:bg-amber-950/30 space-y-1.5">
            <div className="flex items-center gap-1.5 font-bold text-amber-800 dark:text-amber-300">
              <AlertTriangle className="w-4 h-4" /> SPOOF_SUSPECTED &rarr; QUARANTINE
            </div>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              <strong>Condition:</strong> Top Predicted &ne; Claimed AND Confidence &ge; &tau;.
            </p>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              <strong>Action:</strong> Host transitions to <code>QUARANTINED</code>. Forward traffic dropped; port 80/443 redirected to security inspection portal.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-rose-300 dark:border-rose-700 bg-rose-50/50 dark:bg-rose-950/30 space-y-1.5">
            <div className="flex items-center gap-1.5 font-bold text-rose-800 dark:text-rose-300">
              <XCircle className="w-4 h-4" /> UNKNOWN_HARDWARE &rarr; ISOLATE
            </div>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              <strong>Condition:</strong> Confidence &lt; &tau;.
            </p>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              <strong>Action:</strong> Host transitions to <code>ISOLATED</code>. Relegated to non-routable containment VLAN 99.
            </p>
          </div>
        </div>
      </div>

      {/* Honest Operational Limits Box */}
      <div className="p-5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-100/80 dark:bg-slate-800/60 shadow-sm space-y-3">
        <div className="flex items-center gap-2 font-bold text-slate-900 dark:text-white text-sm">
          <Info className="w-4 h-4 text-indigo-500" />
          Honest Scientific Limits & Academic Boundaries
        </div>

        <ul className="list-disc pl-5 space-y-2 text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
          <li>
            <strong>Closed Set of 5 Devices:</strong> The machine learning model was trained strictly on 5 registered smart home IoT device categories (Amazon Echo, Belkin WeMo, Philips Hue, Samsung SmartCam, TP-Link Plug). The 22 other devices in the UNSW dataset are treated as unknown foreign hardware.
          </li>
          <li>
            <strong>Timing Can Be Imitated:</strong> With perfect mathematical knowledge and quantile mapping (s &ge; 0.9), an adversary who can delay their packets can match the target's marginal inter-arrival timing distribution and evade detection.
          </li>
          <li>
            <strong>Replay Attack Blind Spot:</strong> An attacker replaying exact recorded test windows of the target device will PASS verification as <code>TRUSTED</code>. This is a fundamental, honest limitation of passive timing-only verification: timing analysis verifies behavior, not cryptographic freshness. A complete security architecture must combine timing verification with challenge-response or 802.1X certificates.
          </li>
          <li>
            <strong>LAN Threat Model Realism:</strong> Remote internet attackers cannot forge a home device's Layer-2 MAC address across WAN routers. Therefore, the realistic threat modeled by this lab is an <strong>untrusted, compromised, or rogue hardware device physically connected to the local Wi-Fi or Ethernet LAN</strong>.
          </li>
          <li>
            <strong>Firewall Demo Distinction:</strong> The "External Access Attempt" scenario demonstrates the gateway's default-deny firewall policy for unsolicited WAN inbound probes; it is a firewall rule demonstration, not a model timing prediction.
          </li>
        </ul>
      </div>
    </div>
  );
}
