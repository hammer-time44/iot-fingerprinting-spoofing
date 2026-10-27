"""
Offline Evaluation Pipeline for IAT-Based IoT Device Spoofing Detection
========================================================================
Rigorous, reproducible offline evaluation on RECORDED traffic data only:
  - Experiment A: Legitimate traffic verification (source == claimed)
  - Experiment B: Simulated class impersonation (source != claimed)
  - Experiment C: Unseen/foreign hardware evaluation (15 real unknown devices)
  - Experiment D: Controlled timing disturbances (quantile mapping & log-IAT jitter)

Enforces strict feature parity against src/features.py before proceeding.
Saves comprehensive metrics to:
  - results/spoof_<timestamp>/spoof_results.json
  - iot_fingerprint_gui/frontend/public/data/spoof_results.json
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, List, Any
import numpy as np
import pandas as pd

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.features import RAW_FEATURE_NAMES, compute_raw_stats
from src.spoof import (
    ROOT,
    FEATURES,
    TAU,
    load_model,
    load_scaler,
    verdicts,
    verify_stream,
    ScalerWrapper
)

STRENGTHS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
JITTER_K = 1.0  # Log-space standard deviation multiplier at strength 1.0
FD = os.path.join(ROOT, "data", "features")


def load_window_matrix(device_name: str, window_ids: np.ndarray) -> np.ndarray:
    """Load raw log1p-IAT windows (128 columns) for specific window IDs."""
    filepath = os.path.join(FD, f"{device_name}_windows.csv")
    if not os.path.exists(filepath):
        return None
    df = pd.read_csv(filepath)
    cols = [c for c in df.columns if c.startswith("iat_")]
    if not cols:
        return None
    sub = df[df["window_id"].isin(window_ids)].sort_values("window_id")
    return sub[cols].values


def quantile_map(W: np.ndarray, target_pool: np.ndarray, s: float) -> np.ndarray:
    """
    Progressively reshape attacker windows W toward the marginal timing
    distribution of the target device using empirical quantile mapping.
    s = 0.0: pure attacker traffic
    s = 1.0: target marginal distribution
    """
    flat = np.sort(W.ravel())
    if len(flat) == 0 or len(target_pool) == 0:
        return W
    r = np.searchsorted(flat, W, side="right") / len(flat)
    target_q = np.quantile(target_pool, np.clip(r, 0.0, 1.0))
    return (1.0 - s) * W + s * target_q


def apply_jitter(W: np.ndarray, s: float, rng: np.random.Generator) -> np.ndarray:
    """Add controlled Gaussian timing noise in the log1p domain, clipped at 0."""
    noise = rng.normal(0.0, s * JITTER_K, W.shape)
    return np.clip(W + noise, 0.0, None)


def verify_feature_parity(test_df: pd.DataFrame, classes: List[str], scaler: ScalerWrapper) -> None:
    """
    Verify exact mathematical parity between compute_raw_stats from src.features
    and the precomputed features stored in raw_scaled_test.csv.
    FAILS EXPLICITLY with an AssertionError if discrepancy exceeds 1e-4.
    """
    print("\n" + "=" * 80)
    print("  STEP 1: FEATURE EXTRACTION PARITY VERIFICATION")
    print("=" * 80)

    d0 = classes[0]
    dev_test = test_df[test_df["device_label"] == d0].sort_values("window_id")
    sample_ids = dev_test["window_id"].values[:50]

    W = load_window_matrix(d0, sample_ids)
    if W is None or len(W) == 0:
        raise RuntimeError(f"Could not load raw windows for parity check from {d0}_windows.csv")

    computed_features = []
    for row in W:
        stats_dict = compute_raw_stats(row)
        computed_features.append([stats_dict[fn] for fn in FEATURES])

    computed_arr = np.array(computed_features, dtype=np.float64)
    scaled_computed = scaler.transform(computed_arr)

    reference = dev_test[:50][FEATURES].values
    max_abs_diff = float(np.abs(scaled_computed - reference).max())

    print(f"  Target Device:             {d0}")
    print(f"  Windows Evaluated:         {len(sample_ids)}")
    print(f"  Max Absolute Difference:   {max_abs_diff:.2e}")

    # Enforce strict parity requirement
    TOLERANCE = 1e-4
    if max_abs_diff > TOLERANCE:
        raise AssertionError(
            f"FATAL: Feature parity check FAILED! Max difference {max_abs_diff:.2e} "
            f"exceeds tolerance {TOLERANCE:.2e}. Preprocessing pipeline is inconsistent."
        )

    print("  Status:                    PASSED (Parity verified within float precision)")
    print("=" * 80)


def evaluate_legitimate_traffic(
    P_dict: Dict[str, np.ndarray],
    classes: List[str],
    tau: float,
    n_group: int
) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]], Dict[str, Dict[str, float]]]:
    """Experiment A: Legitimate traffic verification across all known classes."""
    legit_false_reject = {}
    legit_breakdown = {}
    device_level_legit = {}

    for d in classes:
        P = P_dict[d]
        v = verdicts(P, classes, d, tau)
        n_total = len(v)

        n_ver = int(np.sum(v == "VERIFIED"))
        n_unk = int(np.sum(v == "UNKNOWN_HARDWARE"))
        n_spf = int(np.sum(v == "SPOOF_SUSPECTED"))

        # False reject = anything NOT verified when traffic is legitimate
        fr_rate = float((n_total - n_ver) / n_total) if n_total > 0 else 0.0

        legit_false_reject[d] = round(fr_rate, 4)
        legit_breakdown[d] = {
            "total_windows": n_total,
            "verified_count": n_ver,
            "verified_rate": round(float(n_ver / n_total), 4),
            "false_rejection_count": n_total - n_ver,
            "false_rejection_rate": round(fr_rate, 4),
            "low_confidence_unknown_rate": round(float(n_unk / n_total), 4),
            "misclassification_spoof_rate": round(float(n_spf / n_total), 4),
        }

        # Multi-window device level
        k = len(P) // n_group
        if k > 0:
            G = P[:k * n_group].reshape(k, n_group, -1).mean(axis=1)
            gv = verdicts(G, classes, d, tau)
            g_ver = int(np.sum(gv == "VERIFIED"))
            device_level_legit[d] = {
                "groups": k,
                "verified_rate": round(float(g_ver / k), 4),
                "false_rejection_rate": round(float((k - g_ver) / k), 4),
            }
        else:
            mean_P = P.mean(axis=0, keepdims=True)
            gv = verdicts(mean_P, classes, d, tau)
            device_level_legit[d] = {
                "groups": 1,
                "verified_rate": round(float(np.mean(gv == "VERIFIED")), 4),
                "false_rejection_rate": round(float(np.mean(gv != "VERIFIED")), 4),
            }

    return legit_false_reject, legit_breakdown, device_level_legit


def evaluate_impersonation(
    P_dict: Dict[str, np.ndarray],
    classes: List[str],
    tau: float,
    n_group: int
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, Dict[str, float]]], Dict[str, Dict[str, float]]]:
    """Experiment B: Simulated class impersonation (source != claimed)."""
    impersonation_matrix = {}
    impersonation_breakdown = {}
    device_level_matrix = {}

    for src in classes:
        P = P_dict[src]
        n_total = len(P)
        impersonation_matrix[src] = {}
        impersonation_breakdown[src] = {}
        device_level_matrix[src] = {}

        for claimed in classes:
            v = verdicts(P, classes, claimed, tau)
            n_ver = int(np.sum(v == "VERIFIED"))
            n_spf = int(np.sum(v == "SPOOF_SUSPECTED"))
            n_unk = int(np.sum(v == "UNKNOWN_HARDWARE"))

            # Total rejection rate (spoof caught or unknown)
            reject_rate = float((n_total - n_ver) / n_total) if n_total > 0 else 0.0

            impersonation_matrix[src][claimed] = round(reject_rate, 4)
            impersonation_breakdown[src][claimed] = {
                "total_windows": n_total,
                "total_rejected_rate": round(reject_rate, 4),
                "spoof_suspected_rate": round(float(n_spf / n_total), 4),
                "unknown_hardware_rate": round(float(n_unk / n_total), 4),
                "verified_bypassed_rate": round(float(n_ver / n_total), 4),
            }

            # Device-level
            k = len(P) // n_group
            if k > 0:
                G = P[:k * n_group].reshape(k, n_group, -1).mean(axis=1)
                gv = verdicts(G, classes, claimed, tau)
                device_level_matrix[src][claimed] = round(float(np.mean(gv != "VERIFIED")), 4)
            else:
                mean_P = P.mean(axis=0, keepdims=True)
                gv = verdicts(mean_P, classes, claimed, tau)
                device_level_matrix[src][claimed] = round(float(np.mean(gv != "VERIFIED")), 4)

    return impersonation_matrix, impersonation_breakdown, device_level_matrix


def evaluate_foreign_devices(
    model: Any,
    scaler: ScalerWrapper,
    classes: List[str],
    tau: float,
    samples_per_dev: int
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, Dict[str, float]]], Dict[str, Any]]:
    """Experiment C: 15 active unseen foreign devices claiming known identities."""
    foreign_matrix = {}
    foreign_breakdown = {}
    replay_unknown = {}

    unk_path = os.path.join(FD, "unknown_devices_features.csv")
    if not os.path.exists(unk_path):
        print("  Notice: unknown_devices_features.csv not found; skipping foreign evaluation.")
        return {}, {}, {}

    U = pd.read_csv(unk_path)
    label_col = next((c for c in ["device_label", "device", "label"] if c in U.columns), None)
    if not label_col:
        print("  Notice: No device label column found in unknown_devices_features.csv")
        return {}, {}, {}

    raw_X = U[FEATURES].values
    scaled_X = scaler.transform(raw_X)
    PU = model.predict_proba(scaled_X)

    for dev_name in sorted(U[label_col].unique()):
        mask = (U[label_col] == dev_name).values
        P_sub = PU[mask]
        n_sub = len(P_sub)

        foreign_matrix[dev_name] = {}
        foreign_breakdown[dev_name] = {}
        replay_unknown[dev_name] = np.round(P_sub[:samples_per_dev * 2], 3).tolist()

        for claimed in classes:
            v = verdicts(P_sub, classes, claimed, tau)
            n_ver = int(np.sum(v == "VERIFIED"))
            n_spf = int(np.sum(v == "SPOOF_SUSPECTED"))
            n_unk = int(np.sum(v == "UNKNOWN_HARDWARE"))

            rej_rate = float((n_sub - n_ver) / n_sub) if n_sub > 0 else 0.0
            foreign_matrix[dev_name][claimed] = round(rej_rate, 4)
            foreign_breakdown[dev_name][claimed] = {
                "total_windows": n_sub,
                "total_rejected_rate": round(rej_rate, 4),
                "spoof_suspected_rate": round(float(n_spf / n_sub), 4),
                "unknown_hardware_rate": round(float(n_unk / n_sub), 4),
                "verified_bypassed_rate": round(float(n_ver / n_sub), 4),
            }

    return foreign_matrix, foreign_breakdown, replay_unknown


def evaluate_mimicry_and_jitter(
    model: Any,
    scaler: ScalerWrapper,
    classes: List[str],
    test_df: pd.DataFrame,
    tau: float,
    rng: np.random.Generator,
    samples_per_dev: int
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Experiment D: Controlled timing disturbances (quantile mapping & jitter)."""
    mimicry_results = {"strengths": STRENGTHS}
    replay_mimic = {}

    # Load test windows for all classes
    W_test = {}
    pool_all = {}
    for d in classes:
        test_wids = test_df[test_df["device_label"] == d]["window_id"].values
        w_mat = load_window_matrix(d, test_wids)
        if w_mat is None:
            print(f"  Notice: could not load raw windows for {d}; skipping mimicry.")
            return mimicry_results, replay_mimic
        W_test[d] = w_mat

        # Load complete device pool for quantile mapping
        df_full = pd.read_csv(os.path.join(FD, f"{d}_windows.csv"))
        cols = [c for c in df_full.columns if c.startswith("iat_")]
        pool_all[d] = df_full[cols].values.ravel()

    for kind in ["quantile", "jitter"]:
        pairs_curves = {}
        for att in classes:
            for tgt in classes:
                if att == tgt:
                    continue
                pair_key = f"{att}>{tgt}"
                curve = []

                for s in STRENGTHS:
                    if kind == "quantile":
                        Wm = quantile_map(W_test[att], pool_all[tgt], s)
                    else:
                        Wm = apply_jitter(W_test[att], s, rng)

                    # Authoritative feature extraction from src.features
                    feats = np.array([[compute_raw_stats(r)[fn] for fn in FEATURES] for r in Wm], dtype=np.float64)
                    scaled = scaler.transform(feats)
                    Pm = model.predict_proba(scaled)

                    # Attacker claims target identity
                    v = verdicts(Pm, classes, tgt, tau)
                    rej_rate = float(np.mean(v != "VERIFIED"))
                    curve.append(round(rej_rate, 4))

                    if kind == "quantile":
                        replay_mimic.setdefault(pair_key, {})[str(s)] = np.round(Pm[:samples_per_dev], 3).tolist()

                pairs_curves[pair_key] = curve

        avg_curve = np.mean(list(pairs_curves.values()), axis=0).tolist()
        mimicry_results[kind] = {
            "avg": [round(float(x), 4) for x in avg_curve],
            "pairs": pairs_curves
        }

    return mimicry_results, replay_mimic


def main():
    parser = argparse.ArgumentParser(description="Run complete offline spoofing-detection evaluation.")
    parser.add_argument("--model", default=None, help="Path to trained model .pkl")
    parser.add_argument("--scaler", default=None, help="Path to scaler .pkl")
    parser.add_argument("--tau", type=float, default=TAU, help=f"Confidence threshold (default {TAU})")
    parser.add_argument("--n", type=int, default=5, help="Number of windows for device-level grouping (default 5)")
    parser.add_argument("--samples", type=int, default=15, help="Number of sample windows to save for UI replay")
    parser.add_argument("--out-dir", default=None, help="Optional custom output directory")

    args = parser.parse_args()
    rng = np.random.default_rng(42)

    model, model_path = load_model(args.model)
    scaler = load_scaler(args.scaler)
    classes = list(model.classes_)

    test_file = os.path.join(FD, "raw_scaled_test.csv")
    if not os.path.exists(test_file):
        raise FileNotFoundError(f"Held-out test split not found: {test_file}")

    test_df = pd.read_csv(test_file).sort_values(["device_label", "window_id"])

    # 1. Parity Check
    verify_feature_parity(test_df, classes, scaler)

    # 2. Extract probability matrices for all known test devices
    P_dict = {}
    for d, group in test_df.groupby("device_label"):
        P_dict[d] = model.predict_proba(group[FEATURES].values)

    # 3. Experiment A: Legitimate traffic
    print("\n" + "=" * 80)
    print("  STEP 2: EXPERIMENT A — LEGITIMATE TRAFFIC VERIFICATION")
    print("=" * 80)
    legit_false_reject, legit_breakdown, dev_level_legit = evaluate_legitimate_traffic(P_dict, classes, args.tau, args.n)
    for d in classes:
        b = legit_breakdown[d]
        print(f"  {d:<24} Verified: {b['verified_rate']*100:5.1f}%  "
              f"False Reject: {b['false_rejection_rate']*100:4.1f}%  "
              f"(Low-Conf: {b['low_confidence_unknown_rate']*100:4.1f}%, Misclass: {b['misclassification_spoof_rate']*100:4.1f}%)")

    # 4. Experiment B: Simulated Impersonation
    print("\n" + "=" * 80)
    print("  STEP 3: EXPERIMENT B — SIMULATED CLASS IMPERSONATION")
    print("=" * 80)
    imp_matrix, imp_breakdown, dev_level_imp = evaluate_impersonation(P_dict, classes, args.tau, args.n)

    all_imp_spoof_rates = []
    all_imp_total_rejections = []
    for s in classes:
        for t in classes:
            if s != t:
                all_imp_spoof_rates.append(imp_breakdown[s][t]["spoof_suspected_rate"])
                all_imp_total_rejections.append(imp_breakdown[s][t]["total_rejected_rate"])

    print(f"  Total Impersonation Pairs Evaluated:  {len(all_imp_spoof_rates)}")
    print(f"  Mean Total Rejection Rate (Caught):   {np.mean(all_imp_total_rejections)*100:.2f}%")
    print(f"  Mean Spoof-Suspected Rate:            {np.mean(all_imp_spoof_rates)*100:.2f}%")
    print(f"  Mean Bypass (False Verification) Rate: {(1.0 - np.mean(all_imp_total_rejections))*100:.2f}%")

    # 5. Experiment C: Foreign / Unseen Devices
    print("\n" + "=" * 80)
    print("  STEP 4: EXPERIMENT C — UNSEEN / FOREIGN HARDWARE EVALUATION")
    print("=" * 80)
    foreign_matrix, foreign_breakdown, replay_unknown = evaluate_foreign_devices(
        model, scaler, classes, args.tau, args.samples
    )
    if foreign_matrix:
        unk_dev_rejections = [np.mean(list(foreign_matrix[d].values())) for d in foreign_matrix]
        print(f"  Foreign Devices Evaluated:            {len(foreign_matrix)}")
        print(f"  Mean Rejection Rate Across Devices:   {np.mean(unk_dev_rejections)*100:.2f}%")

    # 6. Experiment D: Controlled Timing Disturbances (Mimicry & Jitter)
    print("\n" + "=" * 80)
    print("  STEP 5: EXPERIMENT D — TIMING DISTURBANCES & MIMICRY EXPERIMENT")
    print("=" * 80)
    mimicry_data, replay_mimic = evaluate_mimicry_and_jitter(
        model, scaler, classes, test_df, args.tau, rng, args.samples
    )
    if "quantile" in mimicry_data:
        print("  Imitation Strength vs Detection Rate (Quantile Morphing toward Target):")
        for s, r in zip(STRENGTHS, mimicry_data["quantile"]["avg"]):
            print(f"    Strength {s:.1f}: {r*100:5.1f}% detected / rejected")

    # 7. Package replay samples
    replay_known = {}
    for d in classes:
        replay_known[d] = np.round(P_dict[d][:args.samples * 2], 3).tolist()

    # Calculate overall summary metrics
    total_test_windows = sum(len(P_dict[d]) for d in classes)
    total_legit_verified = sum(legit_breakdown[d]["verified_count"] for d in classes)
    overall_legit_verified_rate = float(total_legit_verified / total_test_windows)
    overall_legit_false_reject_rate = float(1.0 - overall_legit_verified_rate)

    results_payload = {
        "metadata": {
            "title": "IAT-Based IoT Device Spoofing Detection Evaluation",
            "model_path": model_path,
            "model_name": os.path.basename(model_path),
            "scaler": "StandardScaler (results/raw_stat_scaler.pkl)",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dataset": "UNSW Sydney Smart Home Benchmark Dataset (Nov 2016)",
            "window_size": 128,
            "tau": args.tau,
            "n_group": args.n,
        },
        "tau": args.tau,
        "model": os.path.basename(os.path.dirname(model_path)) if "step7" in model_path else os.path.basename(model_path),
        "classes": classes,
        "windows": {d: len(P_dict[d]) for d in classes},
        "summary_metrics": {
            "total_test_windows": total_test_windows,
            "overall_legit_verified_rate": round(overall_legit_verified_rate, 4),
            "overall_legit_false_reject_rate": round(overall_legit_false_reject_rate, 4),
            "overall_impersonation_rejection_rate": round(float(np.mean(all_imp_total_rejections)), 4),
            "overall_impersonation_spoof_rate": round(float(np.mean(all_imp_spoof_rates)), 4),
            "impersonation_bypass_rate": round(float(1.0 - np.mean(all_imp_total_rejections)), 4),
        },
        "legit_false_reject": legit_false_reject,
        "legit_breakdown": legit_breakdown,
        "impersonation": imp_matrix,
        "impersonation_breakdown": imp_breakdown,
        "foreign": foreign_matrix,
        "foreign_breakdown": foreign_breakdown,
        "device_level": dev_level_imp,
        "device_level_legit": dev_level_legit,
        "mimicry": mimicry_data,
        "replay": {
            "known": replay_known,
            "unknown": replay_unknown,
            "mimic": replay_mimic,
        }
    }

    # 8. Save results
    ts = time.strftime("%Y%m%d_%H%M%S")
    results_dir = args.out_dir or os.path.join(ROOT, "results", f"spoof_{ts}")
    os.makedirs(results_dir, exist_ok=True)
    res_path = os.path.join(results_dir, "spoof_results.json")

    # GUI frontend locations
    gui_public_data = os.path.join(ROOT, "iot_fingerprint_gui", "frontend", "public", "data", "spoof_results.json")
    legacy_gui_public = os.path.join(ROOT, "iot_fingerprint_gui", "public", "data", "spoof_results.json")
    assets_eval_path = os.path.join(ROOT, "iot_fingerprint_gui", "assets", "evaluation", "spoof_results.json")

    for p in [res_path, gui_public_data, legacy_gui_public, assets_eval_path]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump(results_payload, f, indent=2)

    # Save human-readable summary text
    summary_txt = os.path.join(results_dir, "evaluation_summary.txt")
    with open(summary_txt, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("IAT-BASED IOT DEVICE SPOOFING DETECTION — EVALUATION SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Model: {results_payload['metadata']['model_name']}\n")
        f.write(f"Confidence Threshold (tau): {args.tau:.4f}\n")
        f.write(f"Aggregation Window (N):     {args.n}\n\n")
        f.write("1. LEGITIMATE TRAFFIC (SOURCE == CLAIMED):\n")
        f.write(f"   Total Test Windows:         {total_test_windows}\n")
        f.write(f"   Verified Rate:              {overall_legit_verified_rate*100:.2f}%\n")
        f.write(f"   False Rejection Rate:       {overall_legit_false_reject_rate*100:.2f}%\n")
        for d in classes:
            b = legit_breakdown[d]
            f.write(f"   - {d:<24}: Verified {b['verified_rate']*100:5.1f}%, False Reject {b['false_rejection_rate']*100:4.1f}%\n")
        f.write("\n2. SIMULATED IMPERSONATION (SOURCE != CLAIMED):\n")
        f.write(f"   Mean Claimed-Identity Rejection Rate: {np.mean(all_imp_total_rejections)*100:.2f}%\n")
        f.write(f"   Mean Spoof-Suspected Rate:            {np.mean(all_imp_spoof_rates)*100:.2f}%\n")
        f.write(f"   Impersonation Bypass Rate:            {(1.0 - np.mean(all_imp_total_rejections))*100:.2f}%\n\n")
        f.write("3. TIMING DISTURBANCES & MIMICRY (AVERAGE ACROSS PAIRS):\n")
        if "quantile" in mimicry_data:
            for s, r in zip(STRENGTHS, mimicry_data["quantile"]["avg"]):
                f.write(f"   - Quantile Reshaping Strength {s:.1f}: {r*100:5.1f}% caught / rejected\n")
        f.write("=" * 80 + "\n")

    print("\n" + "=" * 80)
    print("  EVALUATION COMPLETE")
    print("=" * 80)
    print(f"  Artifacts saved to:")
    print(f"    - {res_path}")
    print(f"    - {gui_public_data}")
    print(f"    - {summary_txt}")
    print("=" * 80)


if __name__ == "__main__":
    main()
