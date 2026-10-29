"""
Model Loader & Data Manager for Network Defense Lab.
Loads Random Forest model, scaler, and test windows strictly read-only.
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .config import (
    DEFAULT_MODEL_PATH,
    DEFAULT_SCALER_PATH,
    DATA_FEATURES_DIR,
    DEFAULT_TAU,
    KNOWN_DEVICES,
    PROJECT_ROOT
)

# Ensure project root is in sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.features import compute_raw_stats, RAW_FEATURE_NAMES
from src.spoof import verdicts as spoof_verdicts, load_scaler, load_model, ScalerWrapper


class ModelManager:
    _instance = None

    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        scaler_path: Path = DEFAULT_SCALER_PATH,
        tau: float = DEFAULT_TAU
    ):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.tau = tau

        # Model and scaler
        self.model = None
        self.classes: List[str] = []
        self.scaler_wrapper: Optional[ScalerWrapper] = None
        self.feature_names = RAW_FEATURE_NAMES

        # Data repositories
        self.test_windows_by_device: Dict[str, np.ndarray] = {}
        self.unknown_windows_by_device: Dict[str, np.ndarray] = {}
        self.unknown_device_names: List[str] = []
        self._probs_cache: Dict[str, np.ndarray] = {}

        self._load_model_and_scaler()
        self._load_test_and_unknown_windows()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model_and_scaler(self):
        """Load trained scikit-learn Random Forest model and scaler."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        with open(self.model_path, "rb") as f:
            self.model = pickle.load(f)

        self.model.n_jobs = 1  # Run synchronously to avoid multi-processing worker overhead
        self.classes = list(self.model.classes_)
        self.scaler_wrapper = load_scaler(str(self.scaler_path))

    def _load_test_and_unknown_windows(self):
        """
        Load ONLY test-split windows for known devices to avoid training data leakage.
        Also loads windows for all 15 unseen devices.
        """
        test_split_path = DATA_FEATURES_DIR / "raw_scaled_test.csv"
        if not test_split_path.exists():
            raise FileNotFoundError(f"Test split not found at {test_split_path}")

        test_split_df = pd.read_csv(test_split_path)
        iat_cols = [f"iat_{i}" for i in range(128)]

        for dev in KNOWN_DEVICES:
            dev_win_path = DATA_FEATURES_DIR / f"{dev}_windows.csv"
            if not dev_win_path.exists():
                continue
            win_df = pd.read_csv(dev_win_path)
            
            # Filter strictly by test-split window_ids
            dev_test_ids = set(test_split_df[test_split_df["device_label"] == dev]["window_id"])
            filtered_win = win_df[win_df["window_id"].isin(dev_test_ids)]

            if len(filtered_win) > 0:
                self.test_windows_by_device[dev] = filtered_win[iat_cols].values.astype(np.float64)
            else:
                self.test_windows_by_device[dev] = win_df[iat_cols].values.astype(np.float64)

        # Load Unknown Devices
        unk_path = DATA_FEATURES_DIR / "unknown_devices_windows.csv"
        if unk_path.exists():
            unk_df = pd.read_csv(unk_path)
            dev_col = "device" if "device" in unk_df.columns else "device_label"
            self.unknown_device_names = sorted(list(unk_df[dev_col].unique()))
            for unk_name in self.unknown_device_names:
                sub = unk_df[unk_df[dev_col] == unk_name]
                self.unknown_windows_by_device[unk_name] = sub[iat_cols].values.astype(np.float64)

    def get_device_test_probs(self, device: str) -> np.ndarray:
        """Cached precomputed probability matrix for test windows of known device."""
        if device not in self._probs_cache:
            if device in self.test_windows_by_device:
                windows = self.test_windows_by_device[device]
                feats = self.extract_features(windows)
                self._probs_cache[device] = self.predict_probabilities(feats)
            else:
                return np.zeros((1, len(self.classes)))
        return self._probs_cache[device]

    def get_unknown_device_probs(self, unk_device: str) -> np.ndarray:
        """Cached precomputed probability matrix for unseen device windows."""
        cache_key = f"unk_{unk_device}"
        if cache_key not in self._probs_cache:
            if unk_device in self.unknown_windows_by_device:
                windows = self.unknown_windows_by_device[unk_device]
                feats = self.extract_features(windows)
                self._probs_cache[cache_key] = self.predict_probabilities(feats)
            else:
                return np.zeros((1, len(self.classes)))
        return self._probs_cache[cache_key]

    def extract_features(self, windows_128: np.ndarray) -> np.ndarray:
        """
        Extract 13 raw moments from 128-element log1p(IAT) windows and scale them.
        """
        if windows_128.ndim == 1:
            windows_128 = windows_128.reshape(1, -1)

        feats = []
        for w in windows_128:
            stats = compute_raw_stats(w)
            feats.append([stats[fn] for fn in self.feature_names])

        raw_feat_arr = np.array(feats, dtype=np.float64)
        return self.scaler_wrapper.transform(raw_feat_arr)

    def predict_probabilities(self, scaled_features: np.ndarray) -> np.ndarray:
        """Run Random Forest inference to obtain class probability matrix."""
        return self.model.predict_proba(scaled_features)

    def score_windows(
        self,
        windows_128: np.ndarray,
        claimed_device: str,
        tau: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Process windows end-to-end:
        1. Extract 13 moments
        2. Scale features
        3. Predict probabilities
        4. Apply 3-identity verdict logic
        """
        if tau is None:
            tau = self.tau

        scaled_feats = self.extract_features(windows_128)
        probs = self.predict_probabilities(scaled_feats)
        return self.score_probabilities(probs, claimed_device, tau=tau)

    def score_probabilities(
        self,
        probs: np.ndarray,
        claimed_device: str,
        tau: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Evaluate probability matrix against claimed device and tau."""
        if tau is None:
            tau = self.tau

        if probs.ndim == 1:
            probs = probs.reshape(1, -1)

        results = []
        for P in probs:
            conf = float(np.max(P))
            pred_idx = int(np.argmax(P))
            predicted_device = self.classes[pred_idx]

            if conf < tau:
                verdict = "UNKNOWN_HARDWARE"
            elif predicted_device == claimed_device:
                verdict = "VERIFIED"
            else:
                verdict = "SPOOF_SUSPECTED"

            prob_dict = {cls_name: float(P[i]) for i, cls_name in enumerate(self.classes)}
            results.append({
                "verdict": verdict,
                "confidence": conf,
                "predicted_device": predicted_device,
                "claimed_device": claimed_device,
                "probabilities": prob_dict,
                "tau": tau
            })

        return results

    def compute_device_verdict(
        self,
        window_results: List[Dict[str, Any]],
        claimed_device: str,
        n_windows: int = 5,
        tau: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Compute device-level aggregate verdict over the last n windows.
        If fewer than n windows, return INSUFFICIENT_DATA.
        """
        if tau is None:
            tau = self.tau

        if len(window_results) < n_windows:
            return {
                "verdict": "INSUFFICIENT_DATA",
                "confidence": 0.0,
                "predicted_device": None,
                "claimed_device": claimed_device,
                "mean_probabilities": {cls: 0.0 for cls in self.classes},
                "window_count": len(window_results),
                "required_windows": n_windows,
                "tau": tau
            }

        last_n = window_results[-n_windows:]
        # Average probability distribution
        prob_matrix = np.array([
            [res["probabilities"][cls] for cls in self.classes]
            for res in last_n
        ])
        mean_p = np.mean(prob_matrix, axis=0)
        mean_conf = float(np.max(mean_p))
        pred_idx = int(np.argmax(mean_p))
        predicted_device = self.classes[pred_idx]

        if mean_conf < tau:
            verdict = "UNKNOWN_HARDWARE"
        elif predicted_device == claimed_device:
            verdict = "VERIFIED"
        else:
            verdict = "SPOOF_SUSPECTED"

        return {
            "verdict": verdict,
            "confidence": mean_conf,
            "predicted_device": predicted_device,
            "claimed_device": claimed_device,
            "mean_probabilities": {cls: float(mean_p[i]) for i, cls in enumerate(self.classes)},
            "window_count": len(window_results),
            "required_windows": n_windows,
            "tau": tau
        }
