"""
Batch Benchmark Runner for Network Defense Lab.
Evaluates detection rate, windows-to-detect, legitimate false alarms,
and timing mimicry evasion curves across N seeded trials.
Saves JSON, CSV, and Matplotlib PNG charts in network_guard/results/.
"""

import os
import json
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Any

from .config import RESULTS_DIR, KNOWN_DEVICES, DEFAULT_TAU
from .simulation import SimulationEngine


def run_benchmark(
    n_trials: int = 30,
    max_ticks_per_trial: int = 12,
    seed: int = 42,
    tau: float = DEFAULT_TAU
) -> Dict[str, Any]:
    """
    Execute full batch benchmark across all security scenarios.
    Returns structured results dict.
    """
    rng = np.random.default_rng(seed)
    engine = SimulationEngine(seed=seed, tau=tau)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    scenarios_to_evaluate = [
        "BASELINE",
        "IMPERSONATION",
        "UNKNOWN_HARDWARE",
        "HIJACKED_DEVICE",
        "REPLAY"
    ]

    benchmark_summary = {}

    # 1. Evaluate Standard Scenarios
    for scenario in scenarios_to_evaluate:
        detections = 0
        windows_to_detect_list = []
        false_alarms = 0
        total_eval_windows = 0

        for trial in range(n_trials):
            trial_seed = int(rng.integers(1, 100000))
            engine.seed = trial_seed
            engine.rng = np.random.default_rng(trial_seed)

            # Randomize scenario parameters per trial
            params = {}
            if scenario == "IMPERSONATION":
                src = rng.choice(["SamsungCamera", "PhilipsHue", "BelkinWemoMotionSensor"])
                tgt = "AmazonEcho" if src != "AmazonEcho" else "TPLinkSmartPlug"
                params = {"source_device": src, "claimed_device": tgt}

            elif scenario == "UNKNOWN_HARDWARE":
                unk_devs = engine.model_manager.unknown_device_names
                chosen_unk = rng.choice(unk_devs) if unk_devs else "WithingsSmartScale"
                params = {"unseen_device": chosen_unk, "claimed_device": "AmazonEcho"}

            elif scenario == "HIJACKED_DEVICE":
                params = {"target_host": "host-echo", "hijack_at_tick": 4, "hijack_device": "SamsungCamera"}

            elif scenario == "REPLAY":
                params = {"target_device": "AmazonEcho"}

            engine.configure_scenario(scenario, params)

            trial_detected = False
            detect_tick = None

            for tick in range(1, max_ticks_per_trial + 1):
                t_res = engine.tick()
                
                # Check detection of attacker or hijacked host
                if scenario in ["IMPERSONATION", "UNKNOWN_HARDWARE"]:
                    att_state = t_res["hosts"].get("host-attacker", {}).get("current_state")
                    if att_state in ["QUARANTINED", "ISOLATED"] and not trial_detected:
                        trial_detected = True
                        detect_tick = tick

                elif scenario == "HIJACKED_DEVICE":
                    target_state = t_res["hosts"].get("host-echo", {}).get("current_state")
                    if target_state in ["QUARANTINED", "ISOLATED"] and tick >= 4 and not trial_detected:
                        trial_detected = True
                        detect_tick = tick - 4  # windows after hijacking

                elif scenario == "REPLAY":
                    # In REPLAY, attacker aims to pass as TRUSTED. Detection occurs only if false-alarmed.
                    att_state = t_res["hosts"].get("host-attacker", {}).get("current_state")
                    if att_state in ["QUARANTINED", "ISOLATED"] and not trial_detected:
                        trial_detected = True
                        detect_tick = tick

            if trial_detected:
                detections += 1
                if detect_tick is not None:
                    windows_to_detect_list.append(detect_tick)

            false_alarms += engine.scenario_metrics.get("false_alarms", 0)
            total_eval_windows += engine.scenario_metrics.get("total_windows_evaluated", 0)

        # In REPLAY, detection rate represents how often the system detected an anomaly.
        # Expected to be ~0% because recorded target traffic legitimately matches the profile.
        det_rate = (detections / n_trials) * 100.0
        mean_wtd = float(np.mean(windows_to_detect_list)) if windows_to_detect_list else None
        median_wtd = float(np.median(windows_to_detect_list)) if windows_to_detect_list else None
        fa_rate = (false_alarms / total_eval_windows * 100.0) if total_eval_windows > 0 else 0.0

        benchmark_summary[scenario] = {
            "scenario": scenario,
            "trials": n_trials,
            "detections": detections,
            "detection_rate_pct": round(det_rate, 2),
            "mean_windows_to_detect": round(mean_wtd, 2) if mean_wtd is not None else None,
            "median_windows_to_detect": round(median_wtd, 2) if median_wtd is not None else None,
            "false_alarms": false_alarms,
            "false_alarm_rate_pct": round(fa_rate, 2),
            "description": (
                "Verified honest traffic only (5 known devices)" if scenario == "BASELINE"
                else "Cross-device MAC claim spoofing (detected via timing mismatch)" if scenario == "IMPERSONATION"
                else "Unseen commercial hardware from UNSW dataset (isolated via tau)" if scenario == "UNKNOWN_HARDWARE"
                else "Device compromised and swapped traffic mid-run (detected via state change)" if scenario == "HIJACKED_DEVICE"
                else "Exact recorded target traffic replayed (passes as TRUSTED; documented timing blind spot)"
            )
        }

    # 2. Evaluate Timing Mimicry vs Strength Curve
    mimicry_strengths = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    mimicry_curve = []

    for s in mimicry_strengths:
        s_detections = 0
        s_wtd = []
        for trial in range(n_trials):
            trial_seed = int(rng.integers(1, 100000))
            engine.seed = trial_seed
            engine.rng = np.random.default_rng(trial_seed)
            engine.configure_scenario("TIMING_MIMICRY", {
                "source_device": "SamsungCamera",
                "target_device": "AmazonEcho",
                "strength": s,
                "apply_jitter": False
            })

            detected = False
            for tick in range(1, max_ticks_per_trial + 1):
                t_res = engine.tick()
                att_state = t_res["hosts"].get("host-attacker", {}).get("current_state")
                if att_state in ["QUARANTINED", "ISOLATED"] and not detected:
                    detected = True
                    s_wtd.append(tick)

            # At steady state (end of run), check if attacker was caught vs evaded
            final_state = engine.hosts.get("host-attacker", {}).get("current_state")
            if final_state in ["QUARANTINED", "ISOLATED"]:
                s_detections += 1

        s_det_rate = (s_detections / n_trials) * 100.0
        s_mean_wtd = float(np.mean(s_wtd)) if s_wtd else None
        mimicry_curve.append({
            "strength": round(s, 2),
            "detection_rate_pct": round(s_det_rate, 2),
            "mean_windows_to_detect": round(s_mean_wtd, 2) if s_mean_wtd is not None else None
        })

    # Save Results
    results_payload = {
        "timestamp": timestamp,
        "n_trials": n_trials,
        "tau": tau,
        "seed": seed,
        "summary": benchmark_summary,
        "mimicry_curve": mimicry_curve
    }

    json_path = RESULTS_DIR / f"benchmark_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    # Save Latest Link
    latest_json_path = RESULTS_DIR / "benchmark_latest.json"
    with open(latest_json_path, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    # Save CSV
    csv_rows = []
    for sc_name, sc_data in benchmark_summary.items():
        csv_rows.append(sc_data)
    df_summary = pd.DataFrame(csv_rows)
    csv_path = RESULTS_DIR / "benchmark_summary.csv"
    df_summary.to_csv(csv_path, index=False)

    # Generate Publication Figures
    generate_benchmark_plots(benchmark_summary, mimicry_curve, RESULTS_DIR)

    return results_payload


def generate_benchmark_plots(
    summary: Dict[str, Any],
    mimicry_curve: List[Dict[str, Any]],
    output_dir: Path
):
    """Generate Matplotlib charts from real benchmark data."""
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # 1. Detection Rate by Scenario Bar Chart
    scenarios = [s for s in summary.keys() if s != "BASELINE"]
    rates = [summary[s]["detection_rate_pct"] for s in scenarios]
    colors = ["#4f46e5", "#0284c7", "#10b981", "#64748b"]

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    bars = ax.bar(scenarios, rates, color=colors, width=0.55, edgecolor="#1f2937", linewidth=0.8)
    ax.set_ylim(0, 115)
    ax.set_ylabel("Detection Rate (%)", fontsize=11, fontweight="bold")
    ax.set_title("Network Defense Lab: Attack Detection Rates (N=30 Trials)", fontsize=12, fontweight="bold", pad=12)
    ax.axhline(100, color="gray", linestyle="--", alpha=0.5, linewidth=0.8)

    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 2.5, f"{h:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.tight_layout()
    fig.savefig(output_dir / "benchmark_detection_rates.png")
    plt.close(fig)

    # 2. Mimicry Detection vs Strength Curve
    s_vals = [m["strength"] for m in mimicry_curve]
    m_rates = [m["detection_rate_pct"] for m in mimicry_curve]

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    ax.plot(s_vals, m_rates, marker="o", linewidth=2.5, markersize=7, color="#dc2626", label="Detection Rate (%)")
    ax.set_xlabel("Adversarial Mimicry Strength (s)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Detection Rate (%)", fontsize=11, fontweight="bold")
    ax.set_title("Timing Mimicry Robustness: Detection Rate vs. Morphing Strength", fontsize=12, fontweight="bold", pad=12)
    ax.set_ylim(-5, 105)
    ax.set_xticks(s_vals)
    ax.grid(True, linestyle="--", alpha=0.6)
    
    for x, y in zip(s_vals, m_rates):
        ax.annotate(f"{y:.0f}%", (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, fontweight="bold")

    plt.tight_layout()
    fig.savefig(output_dir / "benchmark_mimicry_curve.png")
    plt.close(fig)

    # 3. Windows to Detect
    wtd_scenarios = ["IMPERSONATION", "UNKNOWN_HARDWARE", "HIJACKED_DEVICE"]
    wtd_means = [summary[s]["mean_windows_to_detect"] or 0 for s in wtd_scenarios]

    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
    bars2 = ax.bar(wtd_scenarios, wtd_means, color="#059669", width=0.45, edgecolor="#1f2937", linewidth=0.8)
    ax.set_ylabel("Mean Windows to First Detect (128 pkts/win)", fontsize=10, fontweight="bold")
    ax.set_title("Detection Latency: Mean Windows-to-Detect", fontsize=11, fontweight="bold", pad=12)
    ax.set_ylim(0, max(wtd_means + [5]) + 2)

    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.2, f"{h:.1f} wins", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.tight_layout()
    fig.savefig(output_dir / "benchmark_windows_to_detect.png")
    plt.close(fig)
