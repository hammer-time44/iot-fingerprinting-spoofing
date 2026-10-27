"""
IAT-Based Claimed-Identity Verification and Spoofing Detection Module
====================================================================
Extends the Random Forest timing classifier and validation-calibrated open-set
threshold to perform active claimed-identity verification:

Outcomes:
  VERIFIED          - Top predicted class matches claimed class AND confidence >= tau
  SPOOF_SUSPECTED   - Top predicted class is a DIFFERENT known class AND confidence >= tau
  UNKNOWN_HARDWARE  - Model confidence < tau (open-set rejection: traffic does not match known profiles)
  INSUFFICIENT_DATA - Fewer than n observation windows are available for device-level decision

Default threshold tau = 0.84 is derived from the 95th percentile anomaly score /
5th percentile max class probability calibrated strictly on the validation split.
"""

import os
import sys
import glob
import pickle
import argparse
from typing import Dict, List, Tuple, Any, Optional, Union
import numpy as np
import pandas as pd

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

# Authoritative feature list from src.features
from src.features import RAW_FEATURE_NAMES, compute_raw_stats
ROOT = PROJ_ROOT
FEATURES = RAW_FEATURE_NAMES
TAU = 0.84  # Calibrated on validation split (95th pct anomaly score = 0.16 -> min confidence 0.84)


class ScalerWrapper:
    """
    Robust wrapper for the feature scaler.
    Handles both scikit-learn StandardScaler instances and dictionary state pickles:
      {"mean": np.ndarray, "std": np.ndarray, "feature_names": list}
    """
    def __init__(self, mean: np.ndarray, std: np.ndarray, feature_names: List[str]):
        self.mean_ = np.asarray(mean, dtype=np.float64)
        self.std_ = np.asarray(std, dtype=np.float64)
        # Prevent division by zero
        self.std_[self.std_ == 0.0] = 1.0
        self.feature_names_ = list(feature_names)

    def transform(self, X: Union[np.ndarray, pd.DataFrame, List[List[float]]]) -> np.ndarray:
        if isinstance(X, pd.DataFrame):
            # Select columns matching feature_names_ if present, else values
            if all(col in X.columns for col in self.feature_names_):
                arr = X[self.feature_names_].values
            else:
                arr = X.values
        else:
            arr = np.asarray(X, dtype=np.float64)

        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        if arr.shape[1] != len(self.mean_):
            raise ValueError(f"Feature dimension mismatch: expected {len(self.mean_)}, got {arr.shape[1]}")

        # Check for NaN / Inf
        if not np.isfinite(arr).all():
            arr = np.nan_to_num(arr, nan=0.0, posinf=1e6, neginf=-1e6)

        return (arr - self.mean_) / self.std_


def load_model(path: Optional[str] = None) -> Tuple[Any, str]:
    """
    Load the trained Random Forest classifier.
    If path is omitted, automatically finds the most recent 13-feature model.
    """
    if path and os.path.exists(path):
        chosen_path = path
    else:
        # Candidate search paths in results and GUI assets
        candidates = []
        for step7_dir in sorted(glob.glob(os.path.join(PROJ_ROOT, "results", "step7_*"))):
            for pattern in ["rf_model.pkl", "rf_raw_model.pkl", "rf*.pkl"]:
                for match in glob.glob(os.path.join(step7_dir, pattern)):
                    if "dwt" not in os.path.basename(match).lower():
                        candidates.append(match)

        gui_model = os.path.join(PROJ_ROOT, "iot_fingerprint_gui", "assets", "model", "rf_model.pkl")
        if os.path.exists(gui_model):
            candidates.append(gui_model)

        if not candidates:
            raise FileNotFoundError("No trained 13-feature Random Forest model found in results/ or iot_fingerprint_gui/assets/model/.")

        # Pick the latest candidate
        chosen_path = candidates[-1]

    with open(chosen_path, "rb") as f:
        model = pickle.load(f)

    # Set single-threaded prediction for fast evaluation
    if hasattr(model, "n_jobs"):
        model.n_jobs = 1

    return model, chosen_path


def load_scaler(path: Optional[str] = None) -> ScalerWrapper:
    """
    Load the fitted feature scaler.
    Supports dictionary state pickles and standard StandardScaler instances.
    """
    if not path or not os.path.exists(path):
        paths_to_try = [
            os.path.join(PROJ_ROOT, "results", "raw_stat_scaler.pkl"),
            os.path.join(PROJ_ROOT, "iot_fingerprint_gui", "assets", "model", "raw_stat_scaler.pkl"),
        ]
        for p in paths_to_try:
            if os.path.exists(p):
                path = p
                break

    if not path or not os.path.exists(path):
        raise FileNotFoundError("Could not find raw_stat_scaler.pkl in results/ or iot_fingerprint_gui/assets/model/.")

    with open(path, "rb") as f:
        obj = pickle.load(f)

    if isinstance(obj, dict):
        if "mean" in obj and "std" in obj:
            return ScalerWrapper(obj["mean"], obj["std"], obj.get("feature_names", RAW_FEATURE_NAMES))
        elif "scaler" in obj and hasattr(obj["scaler"], "transform"):
            s = obj["scaler"]
            return ScalerWrapper(s.mean_, s.std_, getattr(s, "feature_names_", RAW_FEATURE_NAMES))
        else:
            # Check values in dictionary
            for v in obj.values():
                if hasattr(v, "transform") and hasattr(v, "mean_"):
                    return ScalerWrapper(v.mean_, v.std_, getattr(v, "feature_names_", RAW_FEATURE_NAMES))
            raise ValueError(f"Dictionary scaler pickle at {path} does not contain expected keys ('mean', 'std').")
    elif hasattr(obj, "transform") and hasattr(obj, "mean_"):
        return ScalerWrapper(obj.mean_, obj.std_, getattr(obj, "feature_names_", RAW_FEATURE_NAMES))
    else:
        raise TypeError(f"Unrecognized scaler object type: {type(obj)}")


def verdicts(
    P: np.ndarray,
    classes: Union[List[str], np.ndarray],
    claimed: str,
    tau: float = TAU
) -> np.ndarray:
    """
    Vectorized verification decision over probability matrix P of shape (N, num_classes).

    Returns:
      Numpy array of string verdicts:
        'VERIFIED'          if top class == claimed and confidence >= tau
        'SPOOF_SUSPECTED'   if top class != claimed and confidence >= tau
        'UNKNOWN_HARDWARE'  if confidence < tau
    """
    P = np.asarray(P, dtype=np.float64)
    if P.ndim == 1:
        P = P.reshape(1, -1)

    classes_arr = np.asarray(classes)
    top_indices = np.argmax(P, axis=1)
    conf = np.max(P, axis=1)
    preds = classes_arr[top_indices]

    # Default to SPOOF_SUSPECTED when top class differs from claimed identity
    out = np.where(preds == claimed, "VERIFIED", "SPOOF_SUSPECTED").astype(object)

    # Low-confidence predictions fall into UNKNOWN_HARDWARE
    out[conf < tau] = "UNKNOWN_HARDWARE"
    return out


def _detail(
    p: np.ndarray,
    classes: List[str],
    claimed: str,
    tau: float
) -> Dict[str, Any]:
    """Format single observation detail dictionary."""
    p = np.asarray(p, dtype=np.float64)
    i = int(np.argmax(p))
    conf = float(p[i])
    pred = classes[i]
    claimed_prob = float(p[classes.index(claimed)]) if claimed in classes else 0.0

    v = str(verdicts(p[None, :], classes, claimed, tau)[0])

    probs_dict = {classes[idx]: round(float(p[idx]), 4) for idx in range(len(classes))}

    return {
        "verdict": v,
        "predicted": pred,
        "claimed": claimed,
        "confidence": round(conf, 4),
        "claimed_probability": round(claimed_prob, 4),
        "anomaly_score": round(1.0 - conf, 4),
        "threshold": round(tau, 4),
        "probabilities": probs_dict,
    }


def verify(
    x_scaled: Union[np.ndarray, List[float]],
    claimed: str,
    model: Any,
    tau: float = TAU
) -> Dict[str, Any]:
    """
    Evaluate one scaled 13-feature vector against the claimed identity.
    """
    arr = np.asarray(x_scaled, dtype=np.float64).reshape(1, -1)
    P = model.predict_proba(arr)
    classes = list(model.classes_)
    return _detail(P[0], classes, claimed, tau)


def verify_window(
    iats_or_features: Union[np.ndarray, List[float], Dict[str, float]],
    claimed: str,
    model: Any,
    scaler: ScalerWrapper,
    tau: float = TAU,
    is_raw_iats: bool = False
) -> Dict[str, Any]:
    """
    Verify a window given either:
      - 128 raw/log1p IAT values (is_raw_iats=True)
      - 13 unscaled statistical features (is_raw_iats=False)
    """
    if is_raw_iats:
        raw_stats = compute_raw_stats(iats_or_features)
    elif isinstance(iats_or_features, dict):
        raw_stats = iats_or_features
    else:
        # Assume vector of 13 raw features
        arr = np.asarray(iats_or_features, dtype=np.float64)
        if len(arr) == 128:
            raw_stats = compute_raw_stats(arr)
        else:
            raw_stats = {name: float(arr[i]) for i, name in enumerate(RAW_FEATURE_NAMES)}

    feature_vec = np.array([[raw_stats[name] for name in RAW_FEATURE_NAMES]], dtype=np.float64)
    scaled_vec = scaler.transform(feature_vec)
    result = verify(scaled_vec, claimed, model, tau)
    result["features"] = {k: round(v, 4) for k, v in raw_stats.items()}
    return result


def verify_stream(
    P: Union[np.ndarray, List[List[float]]],
    classes: Union[List[str], np.ndarray],
    claimed: str,
    n: int = 5,
    tau: float = TAU,
    method: str = "soft"
) -> Dict[str, Any]:
    """
    Device-level verdict aggregated over multiple consecutive observation windows.

    Args:
      P: Sequence of probability vectors (N x num_classes)
      classes: Ordered class names matching columns of P
      claimed: Registered/claimed device class identity
      n: Number of observation windows required for aggregate verdict
      tau: Confidence threshold (default 0.84)
      method: 'soft' (average probabilities) or 'majority' (majority vote on window verdicts)
    """
    P = np.asarray(P, dtype=np.float64)
    classes_list = list(classes)
    total_obs = len(P)

    if total_obs < n:
        return {
            "verdict": "INSUFFICIENT_DATA",
            "windows_observed": total_obs,
            "windows_required": n,
            "claimed": claimed,
            "reason": f"Need at least {n} observation windows; only {total_obs} provided."
        }

    recent_P = P[-n:]
    window_v = verdicts(recent_P, classes_list, claimed, tau)

    if method == "majority":
        vals, counts = np.unique(window_v, return_counts=True)
        dominant_verdict = vals[np.argmax(counts)]
        top_idx = int(np.argmax(recent_P.mean(axis=0)))
        top_conf = float(recent_P.mean(axis=0)[top_idx])
        return {
            "verdict": str(dominant_verdict),
            "predicted": classes_list[top_idx],
            "claimed": claimed,
            "confidence": round(top_conf, 4),
            "method": "majority_vote",
            "windows_observed": total_obs,
            "windows_used": n,
            "window_verdicts": list(window_v),
            "tally": {str(k): int(c) for k, c in zip(vals, counts)},
        }
    else:
        # Default: Soft voting (mean probability distribution over n windows)
        mean_p = recent_P.mean(axis=0)
        res = _detail(mean_p, classes_list, claimed, tau)
        res["method"] = "soft_voting_mean"
        res["windows_observed"] = total_obs
        res["windows_used"] = n
        res["window_verdicts"] = list(window_v)
        vals, counts = np.unique(window_v, return_counts=True)
        res["tally"] = {str(k): int(c) for k, c in zip(vals, counts)}
        return res


def main():
    parser = argparse.ArgumentParser(description="IoT Fingerprinting Claimed-Identity Verification (Spoof Check)")
    parser.add_argument("--device", required=True, help="True ground-truth source device from dataset")
    parser.add_argument("--claimed", required=True, help="Claimed/registered device class identity")
    parser.add_argument("--model", default=None, help="Path to trained Random Forest model .pkl")
    parser.add_argument("--scaler", default=None, help="Path to scaler .pkl")
    parser.add_argument("--tau", type=float, default=TAU, help=f"Confidence threshold (default {TAU})")
    parser.add_argument("--n", type=int, default=5, help="Number of windows for device-level verdict (default 5)")
    parser.add_argument("--split", default="test", choices=["train", "val", "test"], help="Dataset split to evaluate")

    args = parser.parse_args()

    model, model_path = load_model(args.model)
    scaler = load_scaler(args.scaler)
    classes = list(model.classes_)

    split_file = os.path.join(PROJ_ROOT, "data", "features", f"raw_scaled_{args.split}.csv")
    if not os.path.exists(split_file):
        raise FileNotFoundError(f"Feature split file not found: {split_file}")

    df = pd.read_csv(split_file)
    dev_df = df[df["device_label"] == args.device].sort_values("window_id")

    if len(dev_df) == 0:
        raise ValueError(f"Device '{args.device}' not found in {split_file}. Available: {list(df['device_label'].unique())}")

    X = dev_df[RAW_FEATURE_NAMES].values
    P = model.predict_proba(X)
    v = verdicts(P, classes, args.claimed, args.tau)

    print("=" * 80)
    print("  IOT CLAIMED-IDENTITY VERIFICATION (SPOOF CHECK)")
    print("=" * 80)
    print(f"  Model:                {os.path.basename(model_path)}")
    print(f"  Split:                {args.split} ({len(dev_df)} windows)")
    print(f"  Ground-Truth Device:  {args.device}")
    print(f"  Claimed Identity:     {args.claimed}")
    print(f"  Confidence Threshold: {args.tau:.2f}")
    print(f"  Aggregation Window:   N = {args.n}")
    print("-" * 80)

    print("\n  Window-Level Outcome Breakdown:")
    for outcome in ["VERIFIED", "SPOOF_SUSPECTED", "UNKNOWN_HARDWARE"]:
        count = int(np.sum(v == outcome))
        pct = (count / len(v)) * 100
        print(f"    {outcome:<18} {count:>5} / {len(v)} ({pct:5.1f}%)")

    # Multi-window device-level verification
    stream_res = verify_stream(P, classes, args.claimed, n=args.n, tau=args.tau)
    print("\n  Device-Level Aggregate Decision (last 5 windows):")
    print(f"    Verdict:            {stream_res['verdict']}")
    if "predicted" in stream_res:
        print(f"    Predicted Profile:  {stream_res['predicted']}")
        print(f"    Confidence:         {stream_res['confidence'] * 100:.1f}%")
        print(f"    Claimed Prob:       {stream_res['claimed_probability'] * 100:.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    main()
