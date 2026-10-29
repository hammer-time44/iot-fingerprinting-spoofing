"""
Export script for Network Defense Lab GUI integration.
Generates:
1. public/data/network_guard_data.json (for static client-side replay in React dashboard)
2. network_guard/tests/parity_fixtures.json (200 test vectors to certify JS parity against Python)
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from network_guard.backend.model_loader import ModelManager
from network_guard.backend.policy import evaluate_policy
from network_guard.backend.firewall import generate_firewall_rules
from network_guard.backend.state_machine import HostStateMachine
from src.spoof import verdicts as compute_verdicts
from src.spoof_eval import quantile_map, apply_jitter

PUBLIC_DATA_DIR = ROOT / "iot_fingerprint_gui" / "frontend" / "public" / "data"
DIST_DATA_DIR = ROOT / "iot_fingerprint_gui" / "frontend" / "dist" / "data"
ASSETS_DATA_DIR = ROOT / "iot_fingerprint_gui" / "assets" / "evaluation"
FIXTURES_FILE = ROOT / "network_guard" / "tests" / "parity_fixtures.json"

for d in [PUBLIC_DATA_DIR, DIST_DATA_DIR, ASSETS_DATA_DIR, FIXTURES_FILE.parent]:
    d.mkdir(parents=True, exist_ok=True)

REGISTRY = {
    "host-echo": {
        "id": "host-echo",
        "display_name": "Amazon Echo Dot",
        "ip": "192.168.1.101",
        "mac": "44:65:0D:56:A1:B2",
        "claimed_device": "AmazonEcho"
    },
    "host-wemo": {
        "id": "host-wemo",
        "display_name": "Belkin WeMo Motion",
        "ip": "192.168.1.102",
        "mac": "EC:1A:59:7A:B4:C3",
        "claimed_device": "BelkinWemoMotionSensor"
    },
    "host-hue": {
        "id": "host-hue",
        "display_name": "Philips Hue Bridge",
        "ip": "192.168.1.103",
        "mac": "00:17:88:2E:3D:4E",
        "claimed_device": "PhilipsHue"
    },
    "host-camera": {
        "id": "host-camera",
        "display_name": "Samsung SmartCam",
        "ip": "192.168.1.104",
        "mac": "00:16:6C:AB:CD:EF",
        "claimed_device": "SamsungCamera"
    },
    "host-plug": {
        "id": "host-plug",
        "display_name": "TP-Link Smart Plug",
        "ip": "192.168.1.105",
        "mac": "50:C7:BF:01:23:45",
        "claimed_device": "TPLinkSmartPlug"
    }
}

def get_window_probs(mm, windows_128):
    if len(windows_128) == 0:
        return np.empty((0, len(mm.classes)))
    feats = mm.extract_features(windows_128)
    return mm.predict_probabilities(feats)

def export_network_guard_data():
    print("=== Exporting Network Guard Data for Main Dashboard ===")
    mm = ModelManager.get_instance()
    classes = [str(c) for c in mm.classes]
    tau = float(mm.tau)

    # 1. Meta
    meta = {
        "model_name": "RandomForestClassifier (100 Trees)",
        "classes": classes,
        "tau": tau,
        "window_size": 128,
        "timestamp": datetime.now().isoformat(),
        "source_artifacts": {
            "model": str(mm.model_path.relative_to(ROOT)).replace("\\", "/"),
            "scaler": str(mm.scaler_path.relative_to(ROOT)).replace("\\", "/"),
            "test_split": "data/features/raw_scaled_test.csv"
        }
    }

    # 2. Legit windows & probabilities (up to 60 per known device)
    print("Exporting legitimate host windows (TEST split only)...")
    legit = {}
    for dev in classes:
        windows = mm.test_windows_by_device.get(dev, np.empty((0, 128)))
        count = min(len(windows), 60)
        selected_windows = windows[:count]
        probs = get_window_probs(mm, selected_windows) if count > 0 else np.empty((0, len(classes)))
        
        dev_list = []
        for i in range(count):
            prob_dict = {classes[j]: round(float(probs[i, j]), 4) for j in range(len(classes))}
            top_idx = int(np.argmax(probs[i]))
            top_class = classes[top_idx]
            confidence = round(float(probs[i, top_idx]), 4)
            iat_arr = [round(float(v), 4) for v in selected_windows[i]]
            dev_list.append({
                "probs": prob_dict,
                "top_class": top_class,
                "confidence": confidence,
                "iat": iat_arr
            })
        legit[dev] = dev_list
        print(f"  {dev}: {len(dev_list)} windows exported")

    # 3. Unseen foreign devices (up to 30 windows each, IAT for up to 10)
    print("Exporting unseen device windows...")
    unseen = {}
    for udev in mm.unknown_device_names:
        windows = mm.unknown_windows_by_device.get(udev, np.empty((0, 128)))
        if len(windows) == 0:
            continue
        count = min(len(windows), 30)
        selected_windows = windows[:count]
        probs = get_window_probs(mm, selected_windows)
        
        dev_list = []
        for i in range(count):
            prob_dict = {classes[j]: round(float(probs[i, j]), 4) for j in range(len(classes))}
            top_idx = int(np.argmax(probs[i]))
            top_class = classes[top_idx]
            confidence = round(float(probs[i, top_idx]), 4)
            iat_arr = [round(float(v), 4) for v in selected_windows[i]] if i < 10 else []
            dev_list.append({
                "probs": prob_dict,
                "top_class": top_class,
                "confidence": confidence,
                "iat": iat_arr
            })
        unseen[udev] = dev_list
    print(f"  Exported {len(unseen)} unseen device profiles")

    # 4. Mimicry (quantile mapping + jitter for key pairs and strengths)
    print("Exporting timing mimicry windows...")
    mimicry = {}
    strengths = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    pairs = [
        ("BelkinWemoMotionSensor", "AmazonEcho"),
        ("SamsungCamera", "AmazonEcho"),
        ("PhilipsHue", "SamsungCamera"),
        ("AmazonEcho", "PhilipsHue"),
        ("SamsungCamera", "BelkinWemoMotionSensor"),
    ]

    rng = np.random.default_rng(42)

    for att, tgt in pairs:
        pair_key = f"{att}->{tgt}"
        mimicry[pair_key] = {"quantile": {}, "jitter": {}}
        
        att_windows = mm.test_windows_by_device.get(att, np.empty((0, 128)))
        tgt_windows = mm.test_windows_by_device.get(tgt, np.empty((0, 128)))
        if len(att_windows) == 0 or len(tgt_windows) == 0:
            continue
        
        n_w = min(len(att_windows), 25)
        att_sub = att_windows[:n_w]
        tgt_flat = tgt_windows.ravel()
        
        for s in strengths:
            s_key = f"{s:.1f}"
            # Quantile mapping
            mapped_w = quantile_map(att_sub, tgt_flat, s)
            q_probs = get_window_probs(mm, mapped_w)
            q_list = []
            for i in range(len(q_probs)):
                top_idx = int(np.argmax(q_probs[i]))
                q_list.append({
                    "probs": {classes[j]: round(float(q_probs[i, j]), 4) for j in range(len(classes))},
                    "top_class": classes[top_idx],
                    "confidence": round(float(q_probs[i, top_idx]), 4)
                })
            mimicry[pair_key]["quantile"][s_key] = q_list

            # Jitter mapping
            jitter_w = apply_jitter(att_sub, s, rng)
            j_probs = get_window_probs(mm, jitter_w)
            j_list = []
            for i in range(len(j_probs)):
                top_idx = int(np.argmax(j_probs[i]))
                j_list.append({
                    "probs": {classes[j]: round(float(j_probs[i, j]), 4) for j in range(len(classes))},
                    "top_class": classes[top_idx],
                    "confidence": round(float(j_probs[i, top_idx]), 4)
                })
            mimicry[pair_key]["jitter"][s_key] = j_list
        print(f"  {pair_key}: mapped across 6 strengths")

    # 5. Benchmark latest
    print("Loading benchmark results...")
    benchmark_path = ROOT / "network_guard" / "results" / "benchmark_latest.json"
    if benchmark_path.exists():
        with open(benchmark_path, "r", encoding="utf-8") as f:
            benchmark = json.load(f)
    else:
        benchmark = {}

    # Assemble master dictionary
    master_data = {
        "meta": meta,
        "registry": REGISTRY,
        "legit": legit,
        "unseen": unseen,
        "mimicry": mimicry,
        "benchmark": benchmark,
        "scenarios": [
            {
                "id": "IMPERSONATION",
                "name": "Impersonation Attack",
                "description": "Rogue host sends authentic traffic of device X while falsely claiming to be device Y."
            },
            {
                "id": "UNKNOWN_HARDWARE",
                "name": "Unknown Hardware Injection",
                "description": "Rogue foreign IoT device from 15 unseen models tries to connect using a registered identity."
            },
            {
                "id": "TIMING_MIMICRY",
                "name": "Timing Mimicry Attack",
                "description": "Attacker reshapes inter-arrival times toward the target distribution via quantile mapping or jitter."
            },
            {
                "id": "HIJACKED_DEVICE",
                "name": "Hijacked Internal Host",
                "description": "A legitimate home device operates normally, then starts sending compromised traffic mid-stream."
            },
            {
                "id": "REPLAY",
                "name": "Replay Attack (Blind Spot)",
                "description": "Attacker captures and replays exact authentic packets of the target. Expected to PASS (academic limit)."
            },
            {
                "id": "ACCESS_ATTEMPT",
                "name": "External Access Attempt (Firewall Demo)",
                "description": "Attacker attempts direct WAN connection to internal LAN hosts; blocked by default-deny firewall."
            }
        ]
    }

    # Write to target public paths
    target_paths = [
        PUBLIC_DATA_DIR / "network_guard_data.json",
        DIST_DATA_DIR / "network_guard_data.json",
        ASSETS_DATA_DIR / "network_guard_data.json"
    ]

    for p in target_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(master_data, f, separators=(',', ':'))
        sz_mb = p.stat().st_size / (1024 * 1024)
        print(f"Wrote master JSON to {p} ({sz_mb:.2f} MB)")

    # 6. Parity fixtures (200 random vectors)
    print("Generating 200 parity fixtures for JS unit testing...")
    fixtures = []
    rng_fix = np.random.default_rng(1337)
    
    for i in range(200):
        # Generate random probability vector using Dirichlet
        raw_p = rng_fix.dirichlet(np.ones(5))
        probs_dict = {classes[j]: round(float(raw_p[j]), 4) for j in range(5)}
        claimed_dev = classes[rng_fix.integers(0, 5)]
        
        # Single window verdict
        p_vec = np.array([[probs_dict[cls] for cls in classes]])
        win_v_arr = compute_verdicts(p_vec, classes, claimed_dev, tau=tau)
        win_verdict = str(win_v_arr[0])
        win_top_idx = int(np.argmax(p_vec[0]))
        win_top = classes[win_top_idx]
        win_conf = round(float(p_vec[0, win_top_idx]), 4)
        
        # Simulated 5-window sequence ending with this window
        win_seq_probs = []
        for _ in range(4):
            rp = rng_fix.dirichlet(np.ones(5))
            win_seq_probs.append(rp)
        win_seq_probs.append(raw_p)
        
        # Mean across 5 windows
        mean_p = np.mean(win_seq_probs, axis=0)
        mean_p_dict = {classes[j]: round(float(mean_p[j]), 4) for j in range(5)}
        dev_top_idx = int(np.argmax(mean_p))
        dev_top = classes[dev_top_idx]
        dev_conf = round(float(mean_p[dev_top_idx]), 4)
        
        if dev_conf < tau:
            dev_verdict = "UNKNOWN_HARDWARE"
        elif dev_top == claimed_dev:
            dev_verdict = "VERIFIED"
        else:
            dev_verdict = "SPOOF_SUSPECTED"
        
        # Policy action
        pol = evaluate_policy(dev_verdict)
        action = pol["action"]
        alert = pol["alert"]
        state_map = {
            "VERIFIED": "TRUSTED",
            "SPOOF_SUSPECTED": "QUARANTINED",
            "UNKNOWN_HARDWARE": "ISOLATED",
            "INSUFFICIENT_DATA": "OBSERVING"
        }
        state = state_map.get(dev_verdict, "OBSERVING")
        
        # Firewall text rules
        host_ip = f"192.168.1.{100 + (i % 50)}"
        host_mac = f"00:11:22:33:44:{i % 99:02X}"
        rules = generate_firewall_rules(
            action=action,
            ip=host_ip,
            mac=host_mac,
            claimed_device=claimed_dev,
            target_device=dev_top,
            confidence=dev_conf
        )
        
        fixtures.append({
            "id": i,
            "claimed_device": claimed_dev,
            "probs": probs_dict,
            "window_result": {
                "verdict": win_verdict,
                "confidence": win_conf,
                "top_class": win_top
            },
            "device_result": {
                "verdict": dev_verdict,
                "confidence": dev_conf,
                "top_class": dev_top,
                "mean_probs": mean_p_dict
            },
            "policy": {
                "action": action,
                "state": state,
                "alert": alert
            },
            "rules": rules
        })

    with open(FIXTURES_FILE, "w", encoding="utf-8") as f:
        json.dump({"tau": tau, "classes": classes, "fixtures": fixtures}, f, indent=2)
    print(f"Wrote 200 parity fixtures to {FIXTURES_FILE} ({FIXTURES_FILE.stat().st_size / 1024:.1f} KB)")
    print("Export complete!")

if __name__ == "__main__":
    export_network_guard_data()
