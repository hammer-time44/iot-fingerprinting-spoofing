"""
Generates a PDF document for the Network Defense Lab.
Outputs to:
1. network_guard/docs/NETWORK_DEFENSE_GUIDE.pdf
2. PROJECT_ROOT/NETWORK_DEFENSE_GUIDE.pdf
3. Artifact directory
"""

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
GUARD_DOCS = ROOT / "network_guard" / "docs"
OUT_PDF_GUARD = GUARD_DOCS / "NETWORK_DEFENSE_GUIDE.pdf"
OUT_PDF_ROOT = ROOT / "NETWORK_DEFENSE_GUIDE.pdf"

ARTIFACT_DIR = Path("C:/Users/Murali/.gemini/antigravity/brain/a5e2945a-320a-460a-a19c-173e71d0b0b1")
OUT_PDF_ARTIFACT = ARTIFACT_DIR / "NETWORK_DEFENSE_GUIDE.pdf"

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Network Defense Lab — Comprehensive Technical & Viva Guide</title>
<style>
  @page {
    size: A4;
    margin: 20mm 15mm 20mm 15mm;
    @bottom-center {
      content: "Page " counter(page) " of " counter(pages);
      font-size: 8pt;
      color: #64748b;
      font-family: 'Segoe UI', system-ui, sans-serif;
    }
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #0f172a;
    line-height: 1.5;
    font-size: 9.5pt;
    margin: 0;
    padding: 0;
  }

  /* Cover & Header */
  .cover {
    border-bottom: 2.5px solid #4f46e5;
    padding-bottom: 14px;
    margin-bottom: 20px;
  }
  .title {
    font-size: 20pt;
    font-weight: 800;
    color: #1e1b4b;
    margin: 0 0 6px 0;
    line-height: 1.2;
    letter-spacing: -0.5px;
  }
  .subtitle {
    font-size: 11pt;
    font-weight: 600;
    color: #4f46e5;
    margin: 0 0 10px 0;
  }
  .meta-row {
    display: flex;
    justify-content: space-between;
    font-size: 8.5pt;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
    padding-top: 8px;
    margin-top: 8px;
  }

  /* Badges */
  .badge-group {
    display: flex;
    gap: 6px;
    margin-top: 8px;
  }
  .badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .badge-indigo { background: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe; }
  .badge-emerald { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
  .badge-amber { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }

  /* Headings */
  h2 {
    font-size: 13pt;
    font-weight: 700;
    color: #1e1b4b;
    margin: 22px 0 10px 0;
    padding-bottom: 4px;
    border-bottom: 1.5px solid #cbd5e1;
    page-break-after: avoid;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  h3 {
    font-size: 10.5pt;
    font-weight: 700;
    color: #312e81;
    margin: 14px 0 6px 0;
    page-break-after: avoid;
  }
  h4 {
    font-size: 9.5pt;
    font-weight: 700;
    color: #475569;
    margin: 10px 0 4px 0;
    page-break-after: avoid;
  }

  /* Text & Paragraphs */
  p {
    margin: 0 0 8px 0;
    text-align: justify;
  }

  /* Callout Boxes */
  .callout {
    border-radius: 6px;
    padding: 10px 12px;
    margin: 10px 0;
    font-size: 9pt;
    page-break-inside: avoid;
  }
  .callout-info {
    background: #f8fafc;
    border-left: 4px solid #4f46e5;
    color: #1e293b;
  }
  .callout-warning {
    background: #fffbeb;
    border-left: 4px solid #d97706;
    color: #78350f;
  }
  .callout-success {
    background: #f0fdf4;
    border-left: 4px solid #16a34a;
    color: #14532d;
  }
  .callout-danger {
    background: #fef2f2;
    border-left: 4px solid #dc2626;
    color: #7f1d1d;
  }
  .callout-title {
    font-weight: 700;
    margin-bottom: 4px;
    font-size: 9.5pt;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 14px 0;
    font-size: 8.5pt;
    page-break-inside: avoid;
  }
  th {
    background: #f1f5f9;
    color: #1e293b;
    font-weight: 700;
    text-align: left;
    padding: 6px 8px;
    border-top: 1px solid #cbd5e1;
    border-bottom: 2px solid #94a3b8;
  }
  td {
    padding: 5px 8px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
  }
  tr:nth-child(even) td {
    background: #f8fafc;
  }
  .table-mono {
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 8pt;
  }

  /* Code Blocks */
  pre {
    background: #0f172a;
    color: #f8fafc;
    padding: 8px 10px;
    border-radius: 5px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 8pt;
    overflow-x: hidden;
    line-height: 1.35;
    margin: 6px 0 10px 0;
    page-break-inside: avoid;
    border: 1px solid #334155;
  }
  code {
    background: #f1f5f9;
    color: #3730a3;
    padding: 1px 4px;
    border-radius: 3px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 8.5pt;
    font-weight: 600;
  }

  /* Math Blocks */
  .formula-box {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 12px;
    margin: 8px 0;
    text-align: center;
    font-family: 'Cambria Math', 'Times New Roman', serif;
    font-size: 10pt;
    page-break-inside: avoid;
  }

  /* Diagram SVG Containers */
  .diagram-container {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px;
    margin: 12px 0;
    text-align: center;
    page-break-inside: avoid;
  }
  .diagram-caption {
    font-size: 8pt;
    color: #64748b;
    margin-top: 4px;
    font-weight: 600;
  }

  /* Lists */
  ul, ol {
    margin: 4px 0 8px 0;
    padding-left: 20px;
  }
  li {
    margin-bottom: 3px;
  }

  /* Section Dividers */
  .page-break {
    page-break-before: always;
  }
</style>
</head>
<body>

<!-- Cover / Header -->
<div class="cover">
  <div class="subtitle">PROJECT STUDY & DEFENSE GUIDE</div>
  <div class="title">Network Defense Lab: Dynamic Gateway Policy Engine</div>
  <p style="margin: 0; color: #475569; font-size: 9.5pt;">
    Encrypted IoT Device Fingerprinting via Passive Traffic Timing Analysis & 3-Identity Verification
  </p>
  
  <div class="badge-group">
    <span class="badge badge-indigo">Zero-Payload DPI Bypass</span>
    <span class="badge badge-emerald">100% Math Parity Certified</span>
    <span class="badge badge-amber">Calibrated &tau; = 0.84</span>
    <span class="badge badge-indigo">13 Statistical Moments</span>
  </div>

  <div class="meta-row">
    <span><strong>Author / Repo:</strong> hammer-time44/iot-fingerprinting-spoofing</span>
    <span><strong>Target Platform:</strong> Linux / Windows / Web Static Vercel</span>
    <span><strong>Date:</strong> October 2026</span>
  </div>
</div>

<!-- SECTION 1 -->
<h2>1. Executive Summary & Problem Formulation</h2>

<p>
Smart home Internet of Things (IoT) devices transmit continuous telemetry, audio streams, and command events over public and private networks. To ensure user privacy, modern IoT protocols enforce end-to-end transport layer encryption (TLS 1.3, DTLS, SRTP, and proprietary clouds). Consequently, traditional network security tools face critical operational breakdowns:
</p>

<ul>
  <li><strong>Deep Packet Inspection (DPI) Failure:</strong> Packet payloads are cryptographically opaque. Firewalls cannot inspect content headers, device serial numbers, or application tokens without terminating TLS sessions (which breaks certificate pinning and violates user privacy).</li>
  <li><strong>Layer-2 Identity Forgery:</strong> MAC addresses and IP addresses are unauthenticated plaintext headers. Any attacker on the local Wi-Fi or Ethernet network can clone a trusted MAC address with a single command (<code>macchanger -m &lt;MAC&gt; wlan0</code>).</li>
  <li><strong>Device Constraint Limits:</strong> Inexpensive $2&ndash;$5 smart plugs and sensors lack the memory and cryptographic hardware required to run 802.1X certificates or agent software.</li>
</ul>

<div class="callout callout-info">
  <div class="callout-title">The Core Innovation: Passive Behavioral Fingerprinting</div>
  Even when packet payloads and protocol headers are completely encrypted, <strong>microcontroller timing cannot be hidden</strong>. Physical crystal oscillators, hardware interrupt routines, RTOS thread scheduling, network buffer queues, and application polling loops imprint subtle, distinct <strong>inter-arrival timing (IAT) signatures</strong> onto the traffic. The Network Defense Lab uses these timing moments to autonomously verify device identity and dynamically enforce firewall policies at the gateway without decrypting a single byte.
</div>

<!-- SECTION 2 -->
<h2>2. Threat Model & Operational Scope</h2>

<p>
The threat model realistically characterizes the vulnerabilities of modern smart home and enterprise local networks:
</p>

<table>
  <thead>
    <tr>
      <th style="width: 25%;">Threat Vector</th>
      <th style="width: 45%;">Attacker Capability & Method</th>
      <th style="width: 30%;">Gateway Defense Reaction</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Layer-2 MAC Impersonation</strong></td>
      <td>Attacker clones the registered MAC of a legitimate host (e.g. Amazon Echo) to gain network admission.</td>
      <td><strong>QUARANTINED</strong> &mdash; Behavioral timing moments mismatch claimed identity with high confidence.</td>
    </tr>
    <tr>
      <td><strong>Foreign Hardware Injection</strong></td>
      <td>Attacker connects an unauthorized commercial IoT device (e.g. smart scale, hidden camera) to an open port.</td>
      <td><strong>ISOLATED (VLAN 99)</strong> &mdash; Model confidence falls below &tau; = 0.84 (unseen device signature).</td>
    </tr>
    <tr>
      <td><strong>Compromised Host Takeover</strong></td>
      <td>A legitimate internal device operates normally, then gets infected (botnet malware) mid-stream.</td>
      <td><strong>QUARANTINED</strong> &mdash; 2-tick state transition catches behavioral shift dynamically.</td>
    </tr>
    <tr>
      <td><strong>Timing Perturbation / Mimicry</strong></td>
      <td>Attacker deliberately delays packets via quantile mapping to reshape timings toward the target.</td>
      <td><strong>QUARANTINED</strong> for s &le; 0.8; evades only when quantile match exceeds s &ge; 0.9.</td>
    </tr>
    <tr>
      <td><strong>Replay Attack (Blind Spot)</strong></td>
      <td>Attacker captures and replays exact recorded packets of the target device bit-for-bit.</td>
      <td><strong>ALLOW (TRUSTED)</strong> &mdash; Academic blind spot: timing proves behavior, not freshness.</td>
    </tr>
  </tbody>
</table>

<div class="callout callout-warning">
  <div class="callout-title">Crucial Academic Distinction: LAN vs. WAN Scope</div>
  A remote attacker on the public internet <strong>cannot forge a home device's Layer-2 Ethernet MAC address</strong> across internet routing hops. MAC addresses exist exclusively within the local broadcast domain. Therefore, the threat model realistically addresses <strong>an untrusted, rogue, or compromised hardware device physically connected to the local Wi-Fi or Ethernet LAN</strong>.
</div>

<!-- SECTION 3 -->
<div class="page-break"></div>
<h2>3. The 4-Stage Ingestion & Inference Pipeline</h2>

<div class="diagram-container">
  <svg viewBox="0 0 760 110" style="width: 100%; height: 95px;">
    <!-- Box 1 -->
    <rect x="10" y="15" width="160" height="75" rx="6" fill="#f8fafc" stroke="#6366f1" stroke-width="1.5" />
    <text x="90" y="38" text-anchor="middle" font-size="9" font-weight="bold" fill="#312e81">Stage 1: Packet IAT</text>
    <text x="90" y="55" text-anchor="middle" font-size="7.5" fill="#475569">IAT[i] = t[i] - t[i-1]</text>
    <text x="90" y="72" text-anchor="middle" font-size="7" fill="#64748b">Timestamp diffs only</text>

    <!-- Arrow 1 -->
    <line x1="170" y1="52" x2="195" y2="52" stroke="#6366f1" stroke-width="2" marker-end="url(#arrow)" />
    <polygon points="195,52 188,48 188,56" fill="#6366f1" />

    <!-- Box 2 -->
    <rect x="200" y="15" width="165" height="75" rx="6" fill="#f8fafc" stroke="#6366f1" stroke-width="1.5" />
    <text x="282" y="38" text-anchor="middle" font-size="9" font-weight="bold" fill="#312e81">Stage 2: Log1p & Window</text>
    <text x="282" y="55" text-anchor="middle" font-size="7.5" fill="#475569">w = log(1 + IAT)</text>
    <text x="282" y="72" text-anchor="middle" font-size="7" fill="#64748b">128-Packet Non-Overlapping</text>

    <!-- Arrow 2 -->
    <line x1="365" y1="52" x2="390" y2="52" stroke="#6366f1" stroke-width="2" />
    <polygon points="390,52 383,48 383,56" fill="#6366f1" />

    <!-- Box 3 -->
    <rect x="395" y="15" width="165" height="75" rx="6" fill="#f8fafc" stroke="#6366f1" stroke-width="1.5" />
    <text x="477" y="38" text-anchor="middle" font-size="9" font-weight="bold" fill="#312e81">Stage 3: 13 Moments</text>
    <text x="477" y="55" text-anchor="middle" font-size="7.5" fill="#475569">Mean, Std, Skew, Kurtosis</text>
    <text x="477" y="72" text-anchor="middle" font-size="7" fill="#64748b">P25-P99, Energy, Entropy</text>

    <!-- Arrow 3 -->
    <line x1="560" y1="52" x2="585" y2="52" stroke="#6366f1" stroke-width="2" />
    <polygon points="585,52 578,48 578,56" fill="#6366f1" />

    <!-- Box 4 -->
    <rect x="590" y="15" width="160" height="75" rx="6" fill="#f8fafc" stroke="#6366f1" stroke-width="1.5" />
    <text x="670" y="38" text-anchor="middle" font-size="9" font-weight="bold" fill="#312e81">Stage 4: Random Forest</text>
    <text x="670" y="55" text-anchor="middle" font-size="7.5" fill="#475569">100 Trees + Scaler</text>
    <text x="670" y="72" text-anchor="middle" font-size="7" fill="#64748b">Output: Probs P[c]</text>
  </svg>
  <div class="diagram-caption">Figure 1: End-to-End Passive Traffic Ingestion and Feature Extraction Pipeline</div>
</div>

<h3>3.1 Mathematical Rationale for Logarithmic Compression</h3>
<p>
Network packet intervals span from <strong>microseconds</strong> (hardware loop bursts, $10^{-6}\text{s}$) to <strong>minutes</strong> (keep-alives, $10^2\text{s}$). Feeding raw values causes massive numeric skew and gradient explosion. Applying the monotonic logarithmic transformation:
</p>
<div class="formula-box">
  w_i = \log(1 + \text{IAT}_i) = \ln(1 + t_i - t_{i-1})
</div>
<p>
compresses the multi-order-of-magnitude range into a well-behaved continuous distribution, stabilizing subsequent statistical moments.
</p>

<h3>3.2 The 13 Statistical Moments (Feature Vector)</h3>
<p>
Rather than passing raw sequential packets (which vary with network load and are sensitive to reordering), each 128-packet window is reduced to 13 descriptive statistical moments:
</p>

<table>
  <thead>
    <tr>
      <th style="width: 20%;">Feature Name</th>
      <th style="width: 35%;">Mathematical Definition</th>
      <th style="width: 45%;">Physical Network Interpretation</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>raw_mean</code></td>
      <td>$\mu = \frac{1}{L} \sum_{i=1}^L w_i$</td>
      <td>Overall pacing and throughput density of transmission.</td>
    </tr>
    <tr>
      <td><code>raw_std</code></td>
      <td>$\sigma = \sqrt{\frac{1}{L} \sum (w_i - \mu)^2}$</td>
      <td>Timing jitter and scheduling variability.</td>
    </tr>
    <tr>
      <td><code>raw_min</code> / <code>raw_max</code></td>
      <td>$\min(w_i), \quad \max(w_i)$</td>
      <td>Hardware burst speed limit vs. maximum keep-alive sleep timer.</td>
    </tr>
    <tr>
      <td><code>raw_median</code></td>
      <td>$\text{Percentile}_{50}(w)$</td>
      <td>Central timing tendency robust against network congestion spikes.</td>
    </tr>
    <tr>
      <td><code>raw_skew</code></td>
      <td>$\gamma_1 = \frac{1}{L \sigma^3} \sum (w_i - \mu)^3$</td>
      <td>Asymmetry between short burst packets vs. idle pauses.</td>
    </tr>
    <tr>
      <td><code>raw_kurtosis</code></td>
      <td>$\gamma_2 = \frac{1}{L \sigma^4} \sum (w_i - \mu)^4 - 3$</td>
      <td>Heaviness of distribution tails (frequency of extreme delay pulses).</td>
    </tr>
    <tr>
      <td><code>raw_p25, p75, p95, p99</code></td>
      <td>Quantiles $Q_{0.25}, Q_{0.75}, Q_{0.95}, Q_{0.99}$</td>
      <td>High-resolution cumulative distribution signature of hardware buffers.</td>
    </tr>
    <tr>
      <td><code>raw_energy</code></td>
      <td>$E = \sum_{i=1}^L w_i^2$</td>
      <td>Total squared timing magnitude (reflects persistent idle duration).</td>
    </tr>
    <tr>
      <td><code>raw_entropy</code></td>
      <td>$H = -\sum p_k \log_2(p_k)$</td>
      <td>Shannon information entropy over normalized energy bins.</td>
    </tr>
  </tbody>
</table>

<!-- SECTION 4 -->
<h2>4. The 3-Identity Mathematical Verification Rule</h2>

<p>
The core security check evaluates three distinct identities for every active host:
</p>

<ol>
  <li><strong>Claimed Identity ($c_{\text{claimed}}$):</strong> The registered identity from DHCP/MAC inventory (e.g. "AmazonEcho").</li>
  <li><strong>Predicted Identity ($\hat{y}$):</strong> Top class from Random Forest: $\hat{y} = \arg\max_{c \in \text{known}} P(y = c \mid x)$.</li>
  <li><strong>Prediction Confidence:</strong> Maximum class probability: $\text{Confidence} = \max_{c \in \text{known}} P(y = c \mid x)$.</li>
</ol>

<div class="formula-box">
  \text{Verdict}(x, c_{\text{claimed}}) = \begin{cases}
  \textbf{VERIFIED}, & \text{if } \hat{y} = c_{\text{claimed}} \quad \text{AND} \quad \text{Confidence} \ge \tau \\
  \textbf{SPOOF\_SUSPECTED}, & \text{if } \hat{y} \ne c_{\text{claimed}} \quad \text{AND} \quad \text{Confidence} \ge \tau \\
  \textbf{UNKNOWN\_HARDWARE}, & \text{if } \text{Confidence} < \tau \\
  \textbf{INSUFFICIENT\_DATA}, & \text{if window history } < 5 \text{ windows}
  \end{cases}
</div>

<div class="callout callout-success">
  <div class="callout-title">Validation Calibration of &tau; = 0.84 & Multi-Window Voting</div>
  <strong>Strict Budgeting:</strong> The threshold $\tau = 0.84$ was selected from the 95th percentile of the validation split, enforcing a strict $\le 5\%$ false alarm budget.<br>
  <strong>Multi-Window Soft Voting (n = 5):</strong> Isolated single-window evaluations exhibit a 3.94% false alarm rate due to transient Wi-Fi congestion. Averaging probabilities over rolling 5-window buffers ($5 \times 128 = 640$ packets) reduces the false alarm rate to <strong>exactly 0.0%</strong>.
</div>

<!-- SECTION 5 -->
<div class="page-break"></div>
<h2>5. Dynamic Response Policy & Linux Firewall Synthesis</h2>

<p>
The policy engine is a pure, deterministic function mapping verdicts to network actions and generating syntactically valid Linux <code>iptables</code> and <code>nftables</code> rule text:
</p>

<table>
  <thead>
    <tr>
      <th style="width: 22%;">Verdict</th>
      <th style="width: 18%;">Action & State</th>
      <th style="width: 60%;">Synthesized Linux Firewall Policy (Safe Simulation Text)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>VERIFIED</strong></td>
      <td><code>ALLOW</code><br><strong>TRUSTED</strong></td>
      <td>
        <pre>iptables -A FORWARD -s 192.168.1.101 -m mac --mac-source 44:65:0d:56:a1:b2 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
iptables -A FORWARD -d 192.168.1.101 -m conntrack --ctstate ESTABLISHED -j ACCEPT</pre>
      </td>
    </tr>
    <tr>
      <td><strong>SPOOF_SUSPECTED</strong></td>
      <td><code>QUARANTINE</code><br><strong>QUARANTINED</strong></td>
      <td>
        <pre>iptables -A FORWARD -s 192.168.1.200 -j DROP
iptables -t nat -A PREROUTING -s 192.168.1.200 -p tcp --dport 80 -j DNAT --to-destination 192.168.1.1:8443
iptables -A INPUT -s 192.168.1.200 -p tcp --dport 8443 -j ACCEPT # Captive Portal</pre>
      </td>
    </tr>
    <tr>
      <td><strong>UNKNOWN_HARDWARE</strong></td>
      <td><code>ISOLATE</code><br><strong>ISOLATED</strong></td>
      <td>
        <pre>iptables -A FORWARD -s 192.168.1.200 -j DROP
ip link add link eth0 name eth0.99 type vlan id 99 # Route to containment VLAN 99
ebtables -A FORWARD -s de:ad:be:ef:00:01 -j DROP</pre>
      </td>
    </tr>
    <tr>
      <td><strong>INSUFFICIENT_DATA</strong></td>
      <td><code>OBSERVE</code><br><strong>OBSERVING</strong></td>
      <td>
        <pre>iptables -A FORWARD -s 192.168.1.101 -m limit --limit 30/sec --limit-burst 50 -j ACCEPT
iptables -A FORWARD -s 192.168.1.101 -j LOG --log-prefix "[GATEWAY-OBSERVE] "
iptables -A FORWARD -s 192.168.1.101 -j DROP</pre>
      </td>
    </tr>
  </tbody>
</table>

<!-- SECTION 6 -->
<h2>6. State Machine & Consecutive-Agreement Hysteresis</h2>

<p>
To prevent rapid flapping between states during momentary network spikes, the host state machine enforces <strong>2-tick consecutive agreement hysteresis</strong>:
</p>

<div class="diagram-container">
  <svg viewBox="0 0 740 140" style="width: 100%; height: 120px;">
    <!-- OBSERVING -->
    <rect x="20" y="45" width="130" height="50" rx="8" fill="#f1f5f9" stroke="#64748b" stroke-width="2" />
    <text x="85" y="70" text-anchor="middle" font-size="10" font-weight="bold" fill="#334155">OBSERVING</text>
    <text x="85" y="84" text-anchor="middle" font-size="7.5" fill="#64748b">Initial State</text>

    <!-- TRUSTED -->
    <rect x="280" y="10" width="150" height="45" rx="8" fill="#d1fae5" stroke="#10b981" stroke-width="2" />
    <text x="355" y="32" text-anchor="middle" font-size="9.5" font-weight="bold" fill="#065f46">TRUSTED (ALLOWED)</text>
    <text x="355" y="46" text-anchor="middle" font-size="7" fill="#047857">Full Forwarding</text>

    <!-- QUARANTINED -->
    <rect x="280" y="85" width="150" height="45" rx="8" fill="#fef3c7" stroke="#f59e0b" stroke-width="2" />
    <text x="355" y="107" text-anchor="middle" font-size="9.5" font-weight="bold" fill="#92400e">QUARANTINED</text>
    <text x="355" y="121" text-anchor="middle" font-size="7" fill="#b45309">Port 8443 Redirect</text>

    <!-- ISOLATED -->
    <rect x="560" y="45" width="150" height="50" rx="8" fill="#ffe4e6" stroke="#f43f5e" stroke-width="2" />
    <text x="635" y="70" text-anchor="middle" font-size="9.5" font-weight="bold" fill="#881337">ISOLATED</text>
    <text x="635" y="84" text-anchor="middle" font-size="7" fill="#9f1239">Containment VLAN 99</text>

    <!-- Transitions -->
    <path d="M 150 60 L 280 32" stroke="#10b981" stroke-width="1.5" marker-end="url(#arrow)" />
    <text x="210" y="40" font-size="7" font-weight="bold" fill="#047857">2x VERIFIED</text>

    <path d="M 150 80 L 280 105" stroke="#f59e0b" stroke-width="1.5" />
    <text x="210" y="100" font-size="7" font-weight="bold" fill="#b45309">2x SPOOF</text>

    <path d="M 430 32 L 560 60" stroke="#f43f5e" stroke-width="1.5" />
    <text x="495" y="42" font-size="7" font-weight="bold" fill="#881337">Conf &lt; &tau;</text>

    <path d="M 430 105 L 560 80" stroke="#f43f5e" stroke-width="1.5" />
  </svg>
  <div class="diagram-caption">Figure 2: Finite State Machine Architecture with 2-Tick Hysteresis</div>
</div>

<!-- SECTION 7 -->
<h2>7. Empirical 30-Trial Benchmark Results</h2>

<p>
The evaluation suite was executed across 30 seeded trials ($N=30$) with random temporal offsets:
</p>

<table>
  <thead>
    <tr>
      <th>Security Scenario</th>
      <th>Trials</th>
      <th>Detection Rate</th>
      <th>Mean Windows to Detect</th>
      <th>False Alarm Rate</th>
      <th>Action Enforced</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>BASELINE (Authentic Traffic)</strong></td>
      <td>30</td>
      <td>0.0%</td>
      <td>N/A</td>
      <td><strong>0.0%</strong></td>
      <td><code>ALLOW</code></td>
    </tr>
    <tr>
      <td><strong>IMPERSONATION (MAC Spoof)</strong></td>
      <td>30</td>
      <td><strong>100.0%</strong></td>
      <td><strong>6.0 windows</strong></td>
      <td>0.0%</td>
      <td><code>QUARANTINE</code></td>
    </tr>
    <tr>
      <td><strong>UNKNOWN_HARDWARE (Unseen IoT)</strong></td>
      <td>30</td>
      <td><strong>100.0%</strong></td>
      <td><strong>6.0 windows</strong></td>
      <td>0.0%</td>
      <td><code>ISOLATE</code></td>
    </tr>
    <tr>
      <td><strong>HIJACKED_DEVICE (Mid-Run Takeover)</strong></td>
      <td>30</td>
      <td><strong>100.0%</strong></td>
      <td><strong>2.0 windows</strong> (post-swap)</td>
      <td>0.0%</td>
      <td><code>QUARANTINE</code></td>
    </tr>
    <tr>
      <td><strong>REPLAY (Exact Packet Stream)</strong></td>
      <td>30</td>
      <td><strong>0.0%</strong></td>
      <td>N/A (Evaded)</td>
      <td>0.0%</td>
      <td><code>ALLOW</code> (Blind Spot)</td>
    </tr>
  </tbody>
</table>

<h3>Timing Mimicry Quantile Mapping Curve</h3>
<div class="formula-box">
  w_{\text{mimic}} = (1 - s) \cdot w_{\text{attacker}} + s \cdot Q_{\text{target}}(\text{Rank}(w_{\text{attacker}}))
</div>
<table>
  <thead>
    <tr>
      <th>Quantile Strength ($s$)</th>
      <th>0.0 (Raw Attacker)</th>
      <th>0.2</th>
      <th>0.4</th>
      <th>0.6</th>
      <th>0.8</th>
      <th>1.0 (Exact Match)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Detection Rate (%)</strong></td>
      <td><strong>100.0%</strong></td>
      <td><strong>100.0%</strong></td>
      <td><strong>100.0%</strong></td>
      <td><strong>100.0%</strong></td>
      <td><strong>100.0%</strong></td>
      <td><strong>0.0%</strong></td>
    </tr>
    <tr>
      <td><strong>Gateway Decision</strong></td>
      <td>QUARANTINE</td>
      <td>QUARANTINE</td>
      <td>QUARANTINE</td>
      <td>QUARANTINE</td>
      <td>QUARANTINE</td>
      <td>ALLOW (Evaded)</td>
    </tr>
  </tbody>
</table>

<!-- SECTION 8 -->
<div class="page-break"></div>
<h2>8. Academic Boundaries & Honest Scientific Limits</h2>

<div class="callout callout-warning">
  <div class="callout-title">Honest Limits Must Be Emphasized During Project Defense</div>
  Examiners award top marks when students candidly identify system boundaries rather than claiming 100% universal invulnerability.
</div>

<ol>
  <li><strong>Closed-Set Device Universe:</strong> The model was trained specifically on 5 device classes. Foreign devices are caught because confidence drops below &tau; = 0.84, not because the model recognizes what the foreign device is.</li>
  <li><strong>Replay Attack Blind Spot:</strong> An adversary who captures and replays exact recorded packets of an Echo Dot will be allowed as <code>TRUSTED</code>. Timing analysis verifies <strong>behavioral identity</strong>, not cryptographic freshness. Full production security requires pairing timing analysis with cryptographic challenge-response nonces or 802.1X certificates.</li>
  <li><strong>LAN Layer-2 Boundaries:</strong> An attacker on the internet cannot spoof an internal home MAC across WAN routers. The threat model strictly addresses <strong>untrusted, compromised, or rogue hardware physically connected to the local Wi-Fi or Ethernet LAN</strong>.</li>
  <li><strong>Firewall Policy Separation:</strong> The "External Access Attempt" scenario demonstrates the gateway's perimeter default-deny firewall, not an ML classification result.</li>
</ol>

<!-- SECTION 9 -->
<h2>9. Viva & Examination Defense Master Checklist</h2>

<div class="callout callout-info">
  <div class="callout-title">Q1: Why use 13 statistical moments instead of a Deep Learning 1D-CNN or LSTM?</div>
  <strong>Answer:</strong> 1D-CNNs and LSTMs overfit to sequence ordering and require heavy GPU compute. Statistical moments (mean, variance, skewness, kurtosis, percentiles, signal energy, Shannon entropy) capture the stationary probability density function of hardware timers, require minimal CPU compute suitable for embedded home gateways, and are invariant to minor network packet jitter.
</div>

<div class="callout callout-info">
  <div class="callout-title">Q2: How does the system handle an attacker who spoofs an Echo Dot's MAC address?</div>
  <strong>Answer:</strong> The gateway looks up the MAC in its registry and retrieves the claimed identity "AmazonEcho". The model extracts timing moments from the attacker's actual hardware transmissions. When the timing indicates a camera or PC with confidence &ge; 0.84, the predicted class mismatches the claimed identity, triggering <code>SPOOF_SUSPECTED</code>. After 2 agreeing windows, the state machine transitions the host to <code>QUARANTINED</code>, dropping forward traffic and redirecting HTTP traffic to port 8443.
</div>

<div class="callout callout-info">
  <div class="callout-title">Q3: How was the confidence threshold &tau; = 0.84 calibrated?</div>
  <strong>Answer:</strong> The threshold was determined exclusively on the <strong>validation split</strong> at the 95th percentile of authentic device confidences. It was never tuned on the test split. This guarantees a mathematically calibrated &le; 5% false alarm budget on legitimate traffic.
</div>

<div class="callout callout-info">
  <div class="callout-title">Q4: Why average probabilities over 5 windows?</div>
  <strong>Answer:</strong> An isolated 128-packet window can suffer transient latency spikes due to Wi-Fi bufferbloat. Soft-voting across a rolling buffer of 5 windows ($5 \times 128 = 640$ packets) smooths out momentary noise, reducing legitimate false alarms from 3.94% down to <strong>0.0%</strong>.
</div>

<div class="callout callout-info">
  <div class="callout-title">Q5: Can an attacker evade this system?</div>
  <strong>Answer:</strong> Yes, through: (1) exact replay of recorded packets (because timing verifies behavior, not freshness), or (2) quantile mapping with strength $s \ge 0.9$, artificially buffering packets to mirror the target distribution. This demonstrates that timing analysis is an orthogonal defense-in-depth layer, best combined with cryptographic authentication.
</div>

</body>
</html>
"""

def generate_pdf():
    print("=== Generating Network Defense Lab PDF Guide ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(HTML_CONTENT, wait_until="networkidle")
        
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"}
        )
        browser.close()

    # Save to all target locations
    for target in [OUT_PDF_GUARD, OUT_PDF_ROOT, OUT_PDF_ARTIFACT]:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(pdf_bytes)
        print(f"  Saved PDF to {target} ({len(pdf_bytes) / 1024:.1f} KB)")

    print("PDF generation complete!")

if __name__ == "__main__":
    generate_pdf()
