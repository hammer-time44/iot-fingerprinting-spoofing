# Network Defense Lab — Autonomous Simulated Gateway

> **Encrypted IoT Device Fingerprinting via Traffic Timing Analysis**  
> A self-contained, passive network defense simulation lab demonstrating real-time behavioral fingerprinting, 3-identity verification, and autonomous access control without payload decryption.

---

## 1. Quick Start

### Windows
Double-click `run.bat` or run in PowerShell / Command Prompt:
```cmd
cd network_guard
run.bat
```

### Linux / macOS
Make the script executable and launch:
```bash
cd network_guard
chmod +x run.sh
./run.sh
```

Once running:
- **Dashboard UI**: [http://localhost:5174](http://localhost:5174)
- **Backend API**: [http://127.0.0.1:8766](http://127.0.0.1:8766)
- **Interactive Swagger Docs**: [http://127.0.0.1:8766/docs](http://127.0.0.1:8766/docs)

---

## 2. Manual Installation & Running

If you prefer to start components manually:

### 2.1 Backend Setup
```bash
# Navigate to the repository root
cd /path/to/iot-fingerprinting

# Install Python requirements
pip install -r network_guard/requirements.txt

# Launch FastAPI server on port 8766
python -m uvicorn network_guard.backend.main:app --host 127.0.0.1 --port 8766 --reload
```

### 2.2 Frontend Setup
```bash
# In a separate terminal, navigate to the frontend directory
cd network_guard/frontend

# Install Node dependencies
npm install

# Start Vite development server on port 5174
npm run dev
```

---

## 3. Key Capabilities & Scenarios

1. **Passive Gateway Timing Analysis**:
   - Packets are grouped per host using Layer-2/Layer-3 labels (MAC / IP).
   - 128-packet non-overlapping windows of $\log(1 + \text{IAT})$ are summarized into 13 statistical moments.
   - Scaled using training z-scores and fed into the 100-tree Random Forest classifier.
2. **3-Identity Mathematical Verification**:
   - Compares **Claimed Identity** (Registry) vs. **Observed Traffic Behavior** (Random Forest prediction).
   - If $\max P < \tau$ (calibrated $\tau = 0.84$): classified as `UNKNOWN_HARDWARE` $\to$ **ISOLATE** (containment VLAN 99).
   - If $\arg\max P == \text{Claimed}$: classified as `VERIFIED` $\to$ **ALLOW** (TRUSTED).
   - If $\arg\max P \ne \text{Claimed}$: classified as `SPOOF_SUSPECTED` $\to$ **QUARANTINE** (captive inspection).
   - Multi-window voting ($n=5$) and 2-tick state transition hysteresis eliminate spurious transient alerts.
3. **Interactive Security Scenarios**:
   - `BASELINE`: Normal operation of the 5 registered smart home devices.
   - `IMPERSONATION`: Rogue device replays traffic of device $X$ while claiming to be device $Y$.
   - `UNKNOWN_HARDWARE`: Injection of an unseen IoT device from the 22 foreign devices in the UNSW dataset.
   - `TIMING_MIMICRY`: Adversary reshapes inter-arrival timings using quantile mapping ($s \in [0.0, 1.0]$) and log-domain Gaussian jitter.
   - `HIJACKED_DEVICE`: Registered host transitions from legitimate to compromised behavior mid-stream.
   - `REPLAY`: Exact replay of the target's recorded traffic (demonstrates passive timing verification blind spot).
   - `ACCESS_ATTEMPT`: Direct external WAN probing blocked by gateway default-deny firewall policy.
4. **Text-Only Firewall Generation**:
   - Synthesizes exact, valid `nftables` and `iptables` rules for each transition.
   - **Zero system modification**: rules are displayed for education and export; no OS routing tables or sockets are altered.

---

## 4. Test Suite & Verification

The test suite validates policy decisions, mathematical parity against existing research scripts, feature calculation parity, state machine hysteresis, and REST/WebSocket API endpoints.

To run all 24 automated unit tests:
```bash
python -m pytest network_guard/tests/ -v
```

### Parity Verifications
- **Verdict Parity**: 1,000 randomized Dirichlet probability vectors tested against `src.spoof.verdicts()`. Result: **100.0% exact match**.
- **Feature Calculation Parity**: 150 test windows across all 5 device classes extracted from `raw_scaled_test.csv` compared against re-computed features using `src.features.compute_raw_stats()`. Result: **Maximum discrepancy $1.89 \times 10^{-7} \le 10^{-4}$**.

---

## 5. Statistical Benchmark Suite

To execute the 30-trial batch statistical suite:
```bash
python network_guard/backend/benchmark.py
```
Outputs are saved to `network_guard/results/`:
- `benchmark_latest.json`: Raw trial metrics and timestamps.
- `benchmark_summary.csv`: Aggregated detection rates, latency (windows to detect), and false alarm rates.
- `benchmark_detection_rates.png`: Bar chart of detection percentages across scenarios.
- `benchmark_mimicry_curve.png`: Adversary evasion curve vs. quantile mapping strength ($s = 0.0 \to 1.0$).
- `benchmark_windows_to_detect.png`: Detection latency distribution boxplots.

---

## 6. Zero-Leakage & Isolation Guarantee

The Network Defense Lab strictly respects the host project:
- **Read-Only Access**: Loads trained model weights (`results/step7_*/rf*model.pkl`), scalers (`results/raw_stat_scaler.pkl`), and test-split features (`data/features/raw_scaled_test.csv`) without modification.
- **Strict Isolation**: All newly authored code, dependencies, artifacts, and documentation reside exclusively inside `network_guard/`.
- **Integrity Proof**: A cryptographic SHA-256 hash manifest recorded prior to development is verified upon completion in `network_guard/docs/isolation_proof.txt`.
