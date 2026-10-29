# Network Defense Lab — Architecture & Engineering Decisions (DECISIONS.md)

This log documents every architectural assumption, design default, and fallback implemented in `network_guard/`.

---

## 1. Port Configuration & Coexistence
* **Decision:** Backend defaults to port `8766` and frontend defaults to port `5174`.
* **Rationale:** The existing `iot_fingerprint_gui` service runs on port `8765` (backend) and `5173` (frontend). Using `8766` and `5174` prevents port binding collisions while allowing both environments to operate concurrently.
* **Fallback / Override:** Both ports are fully configurable via environment variables (`PORT` and `VITE_PORT`) and `.env`.

## 2. Model & Scaler Reuse Strategy (Zero Retraining)
* **Decision:** Load the authoritative 100-tree Random Forest model from `results/step7_20261026_151020/rf_model.pkl` and the standard scaler dictionary from `results/raw_stat_scaler.pkl`.
* **Feature Extraction:** Import `compute_raw_stats` and `RAW_FEATURE_NAMES` directly from `src/features.py` read-only by adding project root to `sys.path`.
* **Zero Discrepancy Parity:** Verified that computing features on raw test-split windows and scaling matches `raw_scaled_test.csv` within $1.9 \times 10^{-7}$ (well within the $\le 10^{-4}$ tolerance threshold).

## 3. Ground-Truth Known Device Registry & Display Metadata
* **Decision:** The Home LAN topology registers the 5 known devices trained by the model with realistic display metadata:
  1. `AmazonEcho` &rarr; MAC: `44:65:0D:56:CC:D3`, IP: `192.168.1.101`, Location: "Living Room"
  2. `BelkinWemoMotionSensor` &rarr; MAC: `EC:1A:59:79:F4:89`, IP: `192.168.1.102`, Location: "Hallway"
  3. `PhilipsHue` &rarr; MAC: `00:17:88:24:76:FF`, IP: `192.168.1.103`, Location: "Lighting Hub"
  4. `SamsungCamera` &rarr; MAC: `00:16:6C:AB:6B:88`, IP: `192.168.1.104`, Location: "Front Entrance"
  5. `TPLinkSmartPlug` &rarr; MAC: `50:C7:BF:00:56:39`, IP: `192.168.1.105`, Location: "Home Office"
* **Gateway:** MAC: `52:54:00:12:34:56`, IP: `192.168.1.1` (Defense Gateway / Monitor)
* **Attacker Subnet:** `10.0.0.0/24`, with simulated rogue hosts injected on demand.

## 4. Test-Split Only Replay for Legitimate Simulation
* **Decision:** In simulations, legitimate devices ONLY replay windows present in `data/features/raw_scaled_test.csv` (matched by `window_id` to raw windows in `data/features/<Device>_windows.csv`).
* **Rationale:** Strictly prohibits data leakage and training set memorization artifacts. When windows are exhausted, the index cycles with a deterministic shuffle seed.

## 5. Response Policy & State Machine Rules
* **Decision:**
  * `VERIFIED` &rarr; `ALLOW` (Host moves to `TRUSTED`)
  * `SPOOF_SUSPECTED` &rarr; `QUARANTINE` (Host moves to `QUARANTINED`, traffic dropped/redirected)
  * `UNKNOWN_HARDWARE` &rarr; `ISOLATE` (Host moved to isolated containment VLAN 99)
  * `INSUFFICIENT_DATA` &rarr; `OBSERVE` (Host stays in `OBSERVING`, rate-limited monitoring)
* **Hysteresis:** A host state changes only after **2 consecutive agreeing device-level verdicts** (configurable parameter `hysteresis=2`). This prevents flapping due to single-window burst fluctuations.

## 6. Simulated Scenarios
* **Decision:** Implemented 6 distinct operational scenarios:
  1. `IMPERSONATION`: Known device X timing claiming registered device Y identity.
  2. `UNKNOWN_HARDWARE`: Unseen hardware from 15 UNSW devices claiming a registered identity.
  3. `TIMING_MIMICRY`: Quantile mapping towards target + Gaussian log-domain jitter (reusing logic from `src/spoof_eval.py`).
  4. `HIJACKED_DEVICE`: Normal device transitions to foreign timing mid-session.
  5. `REPLAY`: Recorded target traffic replayed verbatim (documented honest blind spot).
  6. `ACCESS_ATTEMPT`: Gateway firewall default-deny demonstration (clearly labeled policy demo).

## 7. Firewall Rules Generation
* **Decision:** Generates both `iptables` and modern `nftables` commands as text only. All generated rules carry comment markers `(GENERATED TEXT ONLY - NOT APPLIED)` and are never executed against host networking stacks.
