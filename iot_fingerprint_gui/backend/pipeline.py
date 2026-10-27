"""
Core ML and timing feature extraction pipeline for iot_fingerprint_gui.
Reuses the exact 13-feature definitions and trained model from assets/.
"""
import os
import pickle
import numpy as np
from typing import List, Dict, Any, Tuple

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
GUI_DIR = os.path.dirname(BACKEND_DIR)
ASSETS_DIR = os.path.join(GUI_DIR, "assets")
MODEL_DIR = os.path.join(ASSETS_DIR, "model")

MODEL_PATH = os.path.join(MODEL_DIR, "rf_model.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "raw_stat_scaler.pkl")

# Load model and scaler once
with open(MODEL_PATH, "rb") as f:
    rf_model = pickle.load(f)

# Ensure single-threaded prediction to prevent Windows joblib process/thread spawn latency
rf_model.n_jobs = 1

with open(SCALER_PATH, "rb") as f:
    scaler_dict = pickle.load(f)

CLASSES: List[str] = list(rf_model.classes_)
FEATURE_NAMES: List[str] = scaler_dict["feature_names"]
MEAN_VEC: np.ndarray = scaler_dict["mean"]
STD_VEC: np.ndarray = scaler_dict["std"]

# Calibrated rejection threshold (5th percentile on validation: 0.8400)
CALIBRATED_THRESHOLD = 0.8400


def shannon_entropy(values: np.ndarray) -> float:
    """Compute Shannon entropy using normalised squared magnitudes."""
    sq = np.array(values, dtype=np.float64) ** 2
    total = np.sum(sq)
    if total == 0:
        return 0.0
    probs = sq / total
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log2(probs)))


def compute_raw_stats(log1p_iat: np.ndarray) -> Dict[str, float]:
    """
    Compute 13 raw statistical features directly on the log1p-transformed IAT window.
    Exact definition matching src/features.py in training.
    """
    arr = np.array(log1p_iat, dtype=np.float64)

    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr))
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))
    median_val = float(np.median(arr))

    # Skewness (Fisher's definition)
    if std_val > 1e-12:
        skew_val = float(np.mean(((arr - mean_val) / std_val) ** 3))
        kurt_val = float(np.mean(((arr - mean_val) / std_val) ** 4) - 3.0)
    else:
        skew_val = 0.0
        kurt_val = 0.0

    p25 = float(np.percentile(arr, 25))
    p75 = float(np.percentile(arr, 75))
    p95 = float(np.percentile(arr, 95))
    p99 = float(np.percentile(arr, 99))

    energy = float(np.sum(arr ** 2))
    entropy = shannon_entropy(arr)

    return {
        "raw_mean": mean_val,
        "raw_std": std_val,
        "raw_min": min_val,
        "raw_max": max_val,
        "raw_median": median_val,
        "raw_skew": skew_val,
        "raw_kurtosis": kurt_val,
        "raw_p25": p25,
        "raw_p75": p75,
        "raw_p95": p95,
        "raw_p99": p99,
        "raw_energy": energy,
        "raw_entropy": entropy,
    }


def scale_features(feat_dict: Dict[str, float]) -> np.ndarray:
    """Scale 13 features using the training Z-score parameters: (X - mean) / std."""
    raw_vec = np.array([feat_dict[fn] for fn in FEATURE_NAMES], dtype=np.float64)
    scaled_vec = (raw_vec - MEAN_VEC) / STD_VEC
    return scaled_vec.reshape(1, -1)


def predict_window(
    scaled_vector: np.ndarray,
    raw_features: Dict[str, float],
    window_index: int = 0,
    threshold: float = CALIBRATED_THRESHOLD
) -> Dict[str, Any]:
    """
    Execute model inference on one scaled 13-feature vector and apply the decision rule:
      top_prob = highest class probability from predict_proba
      if top_prob >= THRESHOLD: verdict = "KNOWN", label = predicted device
      else: verdict = "UNKNOWN", and report closest known profile
    """
    probs = rf_model.predict_proba(scaled_vector)[0]
    best_idx = int(np.argmax(probs))
    top_prob = float(probs[best_idx])
    closest_device = CLASSES[best_idx]

    probs_dict = {CLASSES[i]: round(float(probs[i]), 4) for i in range(len(CLASSES))}

    if top_prob >= threshold:
        verdict = "KNOWN"
        label = closest_device
    else:
        verdict = "UNKNOWN"
        label = f"Unfamiliar Device (Closest: {closest_device})"

    return {
        "verdict": verdict,
        "label": label,
        "closest_profile": closest_device,
        "top_prob": round(top_prob, 4),
        "probs": probs_dict,
        "threshold": round(threshold, 4),
        "window_index": window_index,
        "features": {k: round(v, 4) for k, v in raw_features.items()}
    }


def process_packet_timestamps(
    timestamps: List[float],
    threshold: float = CALIBRATED_THRESHOLD,
    window_size: int = 128
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Process raw packet arrival timestamps:
      1. Validate non-finite values (NaN, Inf, -Inf)
      2. Compute IAT = t[i] - t[i-1]
      3. Apply log1p(IAT)
      4. Segment into non-overlapping 128-packet windows
      5. Extract 13 features & run model inference
      6. Aggregate device-level decision using standardized soft probability averaging
    """
    if len(timestamps) < 2:
        return [], {"error": "Need at least 2 timestamps to compute inter-arrival times"}

    arr_ts = np.asarray(timestamps, dtype=np.float64)
    if not np.all(np.isfinite(arr_ts)):
        return [], {
            "error": "Invalid timestamp input: timestamps contain non-finite values (NaN, positive infinity, or negative infinity)."
        }

    ts = np.sort(arr_ts)
    raw_iats = np.diff(ts)
    log1p_iats = np.log1p(np.maximum(raw_iats, 0.0))

    num_windows = len(log1p_iats) // window_size
    if num_windows == 0:
        return [], {
            "error": f"Insufficient packets for a complete window. Have {len(timestamps)} packets, need at least {window_size + 1}."
        }

    window_results = []
    labels = []
    confs = []

    for w_idx in range(num_windows):
        win_iats = log1p_iats[w_idx * window_size : (w_idx + 1) * window_size]
        feats = compute_raw_stats(win_iats)
        scaled = scale_features(feats)
        res = predict_window(scaled, feats, window_index=w_idx, threshold=threshold)
        window_results.append(res)

        if res["verdict"] == "KNOWN":
            labels.append(res["closest_profile"])
        confs.append(res["top_prob"])

    total_w = len(window_results)
    known_w = len(labels)

    # Standardized soft probability averaging across all windows
    all_probs = np.array([[w["probs"][c] for c in CLASSES] for w in window_results], dtype=np.float64)
    mean_probs = all_probs.mean(axis=0) if len(all_probs) > 0 else np.zeros(len(CLASSES))
    top_mean_idx = int(np.argmax(mean_probs)) if len(all_probs) > 0 else 0
    top_mean_conf = float(mean_probs[top_mean_idx]) if len(all_probs) > 0 else 0.0
    soft_label = CLASSES[top_mean_idx] if len(all_probs) > 0 else "UNKNOWN"
    soft_verdict = "KNOWN" if top_mean_conf >= threshold else "Unfamiliar Device (Below Threshold)"

    # Legacy majority vote retained for compatibility
    if known_w > total_w / 2:
        from collections import Counter
        counts = Counter(labels)
        dominant, dom_count = counts.most_common(1)[0]
        if dom_count > total_w / 2:
            device_verdict = "KNOWN"
            device_label = dominant
        else:
            device_verdict = "UNKNOWN"
            device_label = "Uncertain / Mixed Known Profiles"
    else:
        device_verdict = "UNKNOWN"
        device_label = "Unfamiliar Device (Below Threshold)"

    summary = {
        "device_verdict": device_verdict,
        "device_label": device_label,
        "soft_verdict": soft_verdict,
        "soft_label": soft_label,
        "soft_confidence": round(top_mean_conf, 4),
        "mean_probabilities": {CLASSES[i]: round(float(mean_probs[i]), 4) for i in range(len(CLASSES))},
        "total_windows": total_w,
        "known_windows": known_w,
        "unknown_windows": total_w - known_w,
        "mean_confidence": round(float(np.mean(confs)), 4) if confs else 0.0,
        "threshold_used": threshold
    }

    return window_results, summary
