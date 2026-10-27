"""
API routes for IAT-based claimed-identity verification and spoofing detection.
"""
import os
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import numpy as np

from ..pipeline import (
    rf_model,
    CLASSES,
    FEATURE_NAMES,
    CALIBRATED_THRESHOLD,
    compute_raw_stats,
    scale_features,
    process_packet_timestamps,
)

router = APIRouter()

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUI_DIR = os.path.dirname(BACKEND_DIR)
EVAL_PATH = os.path.join(GUI_DIR, "assets", "evaluation", "spoof_results.json")
PUBLIC_PATH = os.path.join(GUI_DIR, "frontend", "public", "data", "spoof_results.json")


class SpoofVerifyRequest(BaseModel):
    timestamps: Optional[List[float]] = Field(None, description="Raw arrival timestamps in seconds")
    features: Optional[Dict[str, float]] = Field(None, description="13 unscaled raw statistical features")
    claimed_identity: str = Field(..., description="Registered claimed device class identity")
    threshold: Optional[float] = Field(CALIBRATED_THRESHOLD, description="Confidence rejection threshold")
    n_group: Optional[int] = Field(5, description="Number of windows for device-level decision")


@router.get("/spoof/results")
def get_spoof_results():
    """Return complete offline spoofing evaluation benchmark results."""
    for path in [PUBLIC_PATH, EVAL_PATH]:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)

    raise HTTPException(
        status_code=404,
        detail="Spoof results not found. Run 'python src/spoof_eval.py' to generate benchmark data."
    )


@router.post("/spoof/verify")
def verify_claimed_identity(req: SpoofVerifyRequest):
    """
    Verify observed traffic against a claimed identity:
      - VERIFIED: Predicted class matches claimed class AND confidence >= threshold
      - SPOOF_SUSPECTED: Predicted class != claimed class AND confidence >= threshold
      - UNKNOWN_HARDWARE: Confidence < threshold (insufficient match with known profiles)
      - INSUFFICIENT_DATA: Fewer than n_group windows provided for device-level aggregation

    Device-level decisions standardize on soft probability averaging across windows.
    """
    # 1. Validate claimed identity against supported classifier classes
    if req.claimed_identity not in CLASSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid claimed_identity '{req.claimed_identity}'. Supported classes: {CLASSES}"
        )

    tau = req.threshold if req.threshold is not None else CALIBRATED_THRESHOLD
    n_req = req.n_group if req.n_group is not None else 5

    # 2. Case A: Timestamps stream input
    if req.timestamps:
        if len(req.timestamps) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 timestamps to compute inter-arrival times.")
        windows, summary = process_packet_timestamps(req.timestamps, threshold=tau)
        if "error" in summary:
            raise HTTPException(status_code=400, detail=summary["error"])

        # Evaluate spoofing logic across individual windows
        window_verdicts = []
        window_probs_list = []
        for w in windows:
            top_prob = w["top_prob"]
            pred = w["closest_profile"]
            if top_prob < tau:
                v = "UNKNOWN_HARDWARE"
            elif pred == req.claimed_identity:
                v = "VERIFIED"
            else:
                v = "SPOOF_SUSPECTED"

            probs_row = [w["probs"][c] for c in CLASSES]
            window_probs_list.append(probs_row)

            window_verdicts.append({
                "window_index": w["window_index"],
                "verdict": v,
                "predicted": pred,
                "claimed": req.claimed_identity,
                "confidence": top_prob,
                "claimed_probability": w["probs"].get(req.claimed_identity, 0.0),
                "probabilities": w["probs"],
            })

        # Standardized device-level decision: Soft probability averaging
        total_w = len(windows)
        if total_w < n_req:
            device_verdict = "INSUFFICIENT_DATA"
            device_pred = summary.get("soft_label", "UNKNOWN")
            device_conf = summary.get("soft_confidence", 0.0)
            reason = f"Need at least {n_req} observation windows; only {total_w} provided."
        else:
            recent_probs = np.array(window_probs_list[-n_req:], dtype=np.float64)
            mean_p = recent_probs.mean(axis=0)
            top_idx = int(np.argmax(mean_p))
            device_conf = float(mean_p[top_idx])
            device_pred = CLASSES[top_idx]

            if device_conf < tau:
                device_verdict = "UNKNOWN_HARDWARE"
                reason = f"Averaged confidence {device_conf * 100:.1f}% is below calibrated threshold {tau:.2f}."
            elif device_pred == req.claimed_identity:
                device_verdict = "VERIFIED"
                reason = f"Averaged timing fingerprint matches claimed identity {req.claimed_identity} with {device_conf * 100:.1f}% confidence."
            else:
                device_verdict = "SPOOF_SUSPECTED"
                reason = f"Averaged timing fingerprint resembles {device_pred} ({device_conf * 100:.1f}% confidence), mismatching claimed {req.claimed_identity}."

        return {
            "device_level_verdict": device_verdict,
            "device_predicted": device_pred,
            "claimed_identity": req.claimed_identity,
            "mean_confidence": round(device_conf, 4),
            "total_windows": total_w,
            "windows_used": min(total_w, n_req),
            "aggregation_method": "soft_probability_averaging",
            "threshold": tau,
            "reason": reason,
            "windows": window_verdicts
        }

    # 3. Case B: Single feature vector input
    elif req.features:
        scaled = scale_features(req.features)
        probs = rf_model.predict_proba(scaled)[0]
        top_idx = int(np.argmax(probs))
        top_prob = float(probs[top_idx])
        pred = CLASSES[top_idx]

        if top_prob < tau:
            v = "UNKNOWN_HARDWARE"
        elif pred == req.claimed_identity:
            v = "VERIFIED"
        else:
            v = "SPOOF_SUSPECTED"

        claimed_prob = float(probs[CLASSES.index(req.claimed_identity)])

        return {
            "verdict": v,
            "predicted": pred,
            "claimed": req.claimed_identity,
            "confidence": round(top_prob, 4),
            "claimed_probability": round(claimed_prob, 4),
            "anomaly_score": round(1.0 - top_prob, 4),
            "threshold": round(tau, 4),
            "probabilities": {CLASSES[i]: round(float(probs[i]), 4) for i in range(len(CLASSES))}
        }

    else:
        raise HTTPException(status_code=400, detail="Must provide either 'timestamps' or 'features'.")
