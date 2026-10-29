# Architectural & Engineering Decisions (DECISIONS.md)
## Network Defense Lab: Encrypted IoT Device Fingerprinting via Traffic Timing Analysis

This document records all architectural choices, sensible defaults, and fallback mechanisms selected during the end-to-end development of the **Network Defense Lab** (`network_guard/`).

---

### 1. Model & Scaler Artifact Discovery (Read-Only)
* **Model Selection:** Automatically selects the latest authoritative 13-moment Random Forest model (`results/step7_20261026_151020/rf_model.pkl`, 100 estimators, Gini criterion, single-threaded inference for fast simulation ticks). Any DWT (Discrete Wavelet Transform) model is explicitly excluded.
* **Scaler Selection:** Authoritative `results/raw_stat_scaler.pkl` (StandardScaler fitted strictly on training data across the 13 raw timing moments).
* **Code Reuse Mechanism:** The repository root is prepended to `sys.path` in Python to import existing canonical implementations:
  * `src.features.RAW_FEATURE_NAMES` and `src.features.compute_raw_stats`
  * `src.spoof.verdicts` and `src.spoof.verify_stream`
  * `src.spoof_eval.quantile_map` and `src.spoof_eval.apply_jitter`
  Zero reimplementation of core math or verdict formulas ensures mathematical parity.

---

### 2. Dataset Sourcing & Anti-Leakage Rules
* **Test Split Only for Legitimate Hosts:** To prevent data leakage, legitimate traffic simulation draws exclusively from test-split windows (`data/features/raw_scaled_test.csv` window IDs mapped to raw IAT rows in `data/features/<Device>_windows.csv`).
* **Window Cycling:** When a host finishes its test-split windows (e.g. T-Link Smart Plug has 9 test windows), it seamlessly cycles back to window 0 with consistent sequence tracking.
* **Foreign Hardware (Unknown Devices):** Sourced from `data/features/unknown_devices_windows.csv` containing 15 distinct unseen consumer devices (Withings scale, PixStar frame, LiFX bulb, etc.).

---

### 3. Port & Networking Choices
* **Backend Port:** Defaults to `8766` (configurable via `.env`). This avoids port collision with the existing project GUI running on `8765`.
* **Frontend Port:** Defaults to `5174` (configurable via `.env`). This avoids collision with Vite on `5173`.
* **CORS Policy:** Open to all localhost origins (`http://localhost:*`, `http://127.0.0.1:*`) for development ease.
* **Zero Network Impact:** No raw sockets (`AF_PACKET`), no packet transmission, no kernel firewall modifications (`iptables -A` / `nft add`). All firewall rules are synthesized purely as text representations.

---

### 4. Decision Engine & Response Policy Defaults
* **$\tau$ Threshold:** Default $\tau = 0.84$ read from config and results metadata. Can be adjusted live via the API (`POST /config/tau`) or scenario slider.
* **State Machine & Hysteresis:**
  * Initial State: `OBSERVING`
  * Allowed States: `OBSERVING`, `TRUSTED`, `QUARANTINED`, `ISOLATED`
  * Hysteresis: Requires **2 consecutive agreeing device-level verdicts** before triggering a state transition (prevents flapping from isolated noisy windows).
* **Device-Level Aggregation:**
  * Window size: $N = 5$ windows.
  * Windows $< 5$: Produces `INSUFFICIENT_DATA` &rarr; Policy maps to `OBSERVE` (Allowed with monitoring).
  * Method: Soft probability distribution averaging across the last $N$ windows.
* **Policy Mapping Matrix:**
  * `VERIFIED` &rarr; `ALLOW` (Host transitioned to `TRUSTED`)
  * `SPOOF_SUSPECTED` &rarr; `QUARANTINE` (Host placed in remediation sandbox, alert dispatched)
  * `UNKNOWN_HARDWARE` &rarr; `ISOLATE` (Host moved to isolated untrusted VLAN, alert dispatched)
  * `INSUFFICIENT_DATA` &rarr; `OBSERVE` (Host kept in observation buffer)

---

### 5. Benchmark Trial Count & Determinism
* **Default Benchmark:** 30 trials per scenario (seeded RNG for reproducible timing offsets and jitter generation).
* **Quantile Morphing Grid:** Evaluated across strengths $s \in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]$.
* **True Metric Honesty:** Legitimate false-alarm rates and known blind-spots (such as identical replay attacks) are surfaced transparently in both UI and exported benchmark JSONs without suppression.

