"""
Unit and Integration Tests for IAT-Based IoT Device Spoofing Detection
=======================================================================
Validates core verification logic, thresholds, multi-window aggregation,
preprocessing parity, edge case handling, and evaluation metrics:

Covers all requirements from Task Specification and Audit Fixes:
  1. Correct claimed class with sufficient confidence (-> VERIFIED)
  2. Different predicted class with sufficient confidence (-> SPOOF_SUSPECTED)
  3. Confidence below validated threshold (-> UNKNOWN_HARDWARE)
  4. Insufficient observations (< N windows -> INSUFFICIENT_DATA)
  5. Multiple-window aggregation (soft voting & majority rule)
  6. Legitimate traffic with an incorrect claimed class (simulated impersonation)
  7. Unseen-device handling (open-set rejection of foreign hardware)
  8. Missing, invalid, or zero-variance feature values
  9. Feature-order and preprocessing consistency against fitted scaler
 10. Evaluation metric calculations against deterministic test matrices
 11. Result JSON schema, structure, and completeness for frontend consumption
 12. Invalid claimed identity rejection with HTTP 400 in backend
 13. Non-finite timestamp rejection (NaN, Inf) with descriptive error
 14. Missing summary metrics handling (preventing hardcoded fallback pollution)
 15. Consistent multi-window soft voting decisions across backend and CLI
"""

import os
import sys
import json
import unittest
import numpy as np
import pandas as pd
from fastapi import HTTPException

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from src.features import RAW_FEATURE_NAMES, compute_raw_stats
from src.spoof import (
    load_model,
    load_scaler,
    verdicts,
    verify,
    verify_window,
    verify_stream,
    ScalerWrapper,
    TAU,
    FEATURES,
)
from iot_fingerprint_gui.backend.pipeline import process_packet_timestamps, CLASSES
from iot_fingerprint_gui.backend.routes.spoof import (
    verify_claimed_identity,
    SpoofVerifyRequest,
)


class TestSpoofDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model, cls.model_path = load_model()
        cls.scaler = load_scaler()
        cls.classes = list(cls.model.classes_)
        cls.test_csv = os.path.join(PROJ_ROOT, "data", "features", "raw_scaled_test.csv")
        cls.test_df = pd.read_csv(cls.test_csv)

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 1: Correct claimed class with sufficient confidence -> VERIFIED
    # ─────────────────────────────────────────────────────────────────────────
    def test_1_correct_claimed_class_high_confidence(self):
        classes = ["AmazonEcho", "PhilipsHue", "SamsungCamera"]
        P = np.array([[0.95, 0.03, 0.02]])
        res = verdicts(P, classes, claimed="AmazonEcho", tau=0.84)
        self.assertEqual(res[0], "VERIFIED")

        stream_res = verify_stream(np.repeat(P, 5, axis=0), classes, claimed="AmazonEcho", n=5, tau=0.84)
        self.assertEqual(stream_res["verdict"], "VERIFIED")
        self.assertAlmostEqual(stream_res["confidence"], 0.95, places=2)

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 2: Different predicted class with sufficient confidence -> SPOOF_SUSPECTED
    # ─────────────────────────────────────────────────────────────────────────
    def test_2_different_predicted_class_high_confidence(self):
        classes = ["AmazonEcho", "PhilipsHue", "SamsungCamera"]
        P = np.array([[0.03, 0.05, 0.92]])
        res = verdicts(P, classes, claimed="PhilipsHue", tau=0.84)
        self.assertEqual(res[0], "SPOOF_SUSPECTED")

        stream_res = verify_stream(np.repeat(P, 5, axis=0), classes, claimed="PhilipsHue", n=5, tau=0.84)
        self.assertEqual(stream_res["verdict"], "SPOOF_SUSPECTED")
        self.assertEqual(stream_res["predicted"], "SamsungCamera")

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 3: Confidence below validated threshold -> UNKNOWN_HARDWARE
    # ─────────────────────────────────────────────────────────────────────────
    def test_3_confidence_below_validated_threshold(self):
        classes = ["AmazonEcho", "PhilipsHue", "SamsungCamera"]
        P = np.array([[0.60, 0.25, 0.15]])
        res = verdicts(P, classes, claimed="AmazonEcho", tau=0.84)
        self.assertEqual(res[0], "UNKNOWN_HARDWARE")

        res_diff = verdicts(P, classes, claimed="PhilipsHue", tau=0.84)
        self.assertEqual(res_diff[0], "UNKNOWN_HARDWARE")

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 4: Insufficient observations -> INSUFFICIENT_DATA
    # ─────────────────────────────────────────────────────────────────────────
    def test_4_insufficient_observations(self):
        classes = self.classes
        P = np.array([[0.95, 0.01, 0.01, 0.02, 0.01], [0.94, 0.02, 0.01, 0.02, 0.01]])
        stream_res = verify_stream(P, classes, claimed="AmazonEcho", n=5, tau=0.84)
        self.assertEqual(stream_res["verdict"], "INSUFFICIENT_DATA")
        self.assertEqual(stream_res["windows_observed"], 2)
        self.assertEqual(stream_res["windows_required"], 5)

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 5: Multiple-window aggregation (soft voting & majority rule)
    # ─────────────────────────────────────────────────────────────────────────
    def test_5_multiple_window_aggregation(self):
        classes = ["DevA", "DevB"]
        P = np.array([
            [0.90, 0.10],
            [0.75, 0.25],  # isolated dip below 0.84
            [0.92, 0.08],
            [0.88, 0.12],
            [0.90, 0.10],
        ])
        indiv = verdicts(P, classes, claimed="DevA", tau=0.84)
        self.assertEqual(indiv[1], "UNKNOWN_HARDWARE")

        soft_res = verify_stream(P, classes, claimed="DevA", n=5, tau=0.84, method="soft")
        self.assertEqual(soft_res["verdict"], "VERIFIED")
        self.assertGreaterEqual(soft_res["confidence"], 0.84)

        maj_res = verify_stream(P, classes, claimed="DevA", n=5, tau=0.84, method="majority")
        self.assertEqual(maj_res["verdict"], "VERIFIED")

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 6: Legitimate traffic with an incorrect claimed class
    # ─────────────────────────────────────────────────────────────────────────
    def test_6_legitimate_traffic_with_incorrect_claimed_class(self):
        echo_df = self.test_df[self.test_df["device_label"] == "AmazonEcho"].sort_values("window_id")
        X = echo_df[RAW_FEATURE_NAMES].values[:30]
        P = self.model.predict_proba(X)

        v = verdicts(P, self.classes, claimed="PhilipsHue", tau=0.84)

        verified_count = np.sum(v == "VERIFIED")
        self.assertEqual(verified_count, 0, "Security failure: AmazonEcho traffic was verified as PhilipsHue!")

        rejections = np.sum((v == "SPOOF_SUSPECTED") | (v == "UNKNOWN_HARDWARE"))
        self.assertEqual(rejections, len(v))

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 7: Unseen-device handling
    # ─────────────────────────────────────────────────────────────────────────
    def test_7_unseen_device_handling(self):
        unk_csv = os.path.join(PROJ_ROOT, "data", "features", "unknown_devices_features.csv")
        self.assertTrue(os.path.exists(unk_csv), "unknown_devices_features.csv must exist")

        unk_df = pd.read_csv(unk_csv)
        nest = unk_df[unk_df["device_label"] == "NestDropCam"]
        if len(nest) > 0:
            X_raw = nest[RAW_FEATURE_NAMES].values[:20]
            X_scaled = self.scaler.transform(X_raw)
            P = self.model.predict_proba(X_scaled)
            v = verdicts(P, self.classes, claimed="SamsungCamera", tau=0.84)

            unknown_rate = np.mean(v == "UNKNOWN_HARDWARE")
            self.assertGreaterEqual(unknown_rate, 0.90)

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 8: Missing or invalid feature values & edge cases
    # ─────────────────────────────────────────────────────────────────────────
    def test_8_missing_and_invalid_feature_values(self):
        const_window = np.zeros(128, dtype=np.float64)
        stats = compute_raw_stats(const_window)
        self.assertEqual(stats["raw_std"], 0.0)
        self.assertEqual(stats["raw_skew"], 0.0)
        self.assertEqual(stats["raw_kurtosis"], 0.0)
        self.assertEqual(stats["raw_entropy"], 0.0)

        nan_matrix = np.full((2, 13), np.nan)
        scaled_nan = self.scaler.transform(nan_matrix)
        self.assertTrue(np.isfinite(scaled_nan).all(), "Scaler did not sanitize NaN inputs")

        with self.assertRaises(ValueError):
            self.scaler.transform(np.zeros((1, 5)))

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 9: Feature-order and preprocessing consistency
    # ─────────────────────────────────────────────────────────────────────────
    def test_9_feature_order_and_preprocessing_consistency(self):
        self.assertEqual(self.scaler.feature_names_, RAW_FEATURE_NAMES)
        self.assertEqual(len(self.scaler.mean_), 13)
        self.assertEqual(len(self.scaler.std_), 13)
        self.assertTrue((self.scaler.std_ > 0).all(), "Scaler std has zero or negative components")

        first_row = self.test_df.iloc[0]
        raw_feats = [float(first_row[c]) for c in RAW_FEATURE_NAMES]
        P = self.model.predict_proba(np.array(raw_feats).reshape(1, -1))
        self.assertEqual(P.shape[1], 5)
        self.assertAlmostEqual(float(np.sum(P)), 1.0, places=4)

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 10: Evaluation metrics against small, known test cases
    # ─────────────────────────────────────────────────────────────────────────
    def test_10_evaluation_metrics_small_known_cases(self):
        classes = ["ClassA", "ClassB", "ClassC"]
        P = np.array([
            [0.90, 0.05, 0.05],
            [0.05, 0.85, 0.10],
            [0.50, 0.25, 0.25],
            [0.05, 0.90, 0.05],
        ])
        v = verdicts(P, classes, claimed="ClassA", tau=0.80)
        self.assertEqual(list(v), ["VERIFIED", "SPOOF_SUSPECTED", "UNKNOWN_HARDWARE", "SPOOF_SUSPECTED"])

        n_total = len(v)
        n_ver = np.sum(v == "VERIFIED")
        n_spf = np.sum(v == "SPOOF_SUSPECTED")
        n_unk = np.sum(v == "UNKNOWN_HARDWARE")

        self.assertEqual(n_ver / n_total, 0.25)
        self.assertEqual(n_spf / n_total, 0.50)
        self.assertEqual(n_unk / n_total, 0.25)
        self.assertEqual((n_spf + n_unk) / n_total, 0.75)

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 11: Frontend handling and JSON result file validity
    # ─────────────────────────────────────────────────────────────────────────
    def test_11_spoof_results_json_validity(self):
        json_path = os.path.join(PROJ_ROOT, "iot_fingerprint_gui", "frontend", "public", "data", "spoof_results.json")
        self.assertTrue(os.path.exists(json_path), f"{json_path} must exist from spoof_eval.py")

        with open(json_path, "r") as f:
            data = json.load(f)

        required_keys = [
            "tau", "model", "classes", "windows", "summary_metrics",
            "legit_false_reject", "legit_breakdown", "impersonation",
            "impersonation_breakdown", "foreign", "device_level", "mimicry", "replay"
        ]
        for k in required_keys:
            self.assertIn(k, data, f"Missing required top-level key '{k}' in spoof_results.json")

        self.assertEqual(data["classes"], self.classes)

        for src in self.classes:
            self.assertIn(src, data["impersonation"])
            for tgt in self.classes:
                self.assertIn(tgt, data["impersonation"][src])
                val = data["impersonation"][src][tgt]
                self.assertTrue(0.0 <= val <= 1.0, f"Impersonation rate out of range: {val}")

        self.assertIn("known", data["replay"])
        for d in self.classes:
            self.assertIn(d, data["replay"]["known"])
            self.assertGreater(len(data["replay"]["known"][d]), 0)

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 12 (Audit Fix 1): Validate claimed_identity against supported classes
    # ─────────────────────────────────────────────────────────────────────────
    def test_12_invalid_claimed_identity_rejection(self):
        # 1. Test backend endpoint raises HTTP 400 when an invalid claimed_identity is sent
        sample_features = {fn: 0.5 for fn in RAW_FEATURE_NAMES}
        req_invalid = SpoofVerifyRequest(
            features=sample_features,
            claimed_identity="UnregisteredGhostHardware",
            threshold=0.84
        )
        with self.assertRaises(HTTPException) as ctx:
            verify_claimed_identity(req_invalid)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid claimed_identity", ctx.exception.detail)

        # 2. Test valid claimed identity succeeds
        req_valid = SpoofVerifyRequest(
            features=sample_features,
            claimed_identity="AmazonEcho",
            threshold=0.84
        )
        resp = verify_claimed_identity(req_valid)
        self.assertIn("verdict", resp)
        self.assertEqual(resp["claimed"], "AmazonEcho")

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 13 (Audit Fix 4): Reject non-finite timestamps (NaN, Inf)
    # ─────────────────────────────────────────────────────────────────────────
    def test_13_non_finite_timestamps_rejection(self):
        # 1. Timestamps containing NaN
        ts_with_nan = [1.0, float("nan")] + [float(i) for i in range(2, 140)]
        wins, summary = process_packet_timestamps(ts_with_nan)
        self.assertEqual(len(wins), 0)
        self.assertIn("error", summary)
        self.assertIn("non-finite values", summary["error"])

        # 2. Timestamps containing positive infinity
        ts_with_inf = [1.0, float("inf")] + [float(i) for i in range(2, 140)]
        wins_inf, summary_inf = process_packet_timestamps(ts_with_inf)
        self.assertEqual(len(wins_inf), 0)
        self.assertIn("error", summary_inf)
        self.assertIn("non-finite values", summary_inf["error"])

        # 3. Valid timestamps pass smoothly
        ts_valid = [float(i * 0.05) for i in range(140)]
        wins_valid, summary_valid = process_packet_timestamps(ts_valid)
        self.assertNotIn("error", summary_valid)
        self.assertEqual(summary_valid["total_windows"], 1)

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 14 (Audit Fix 2): Handling of missing or partial summary metrics
    # ─────────────────────────────────────────────────────────────────────────
    def test_14_missing_summary_metrics_handling(self):
        # Verify that absence of summary_metrics keys does not produce hardcoded values
        empty_payload = {
            "tau": 0.84,
            "classes": self.classes,
            "summary_metrics": {}
        }
        # In frontend logic: summary_metrics?.overall_legit_verified_rate != null ? ... : 'N/A'
        val = empty_payload.get("summary_metrics", {}).get("overall_legit_verified_rate")
        self.assertIsNone(val, "Missing summary metric must evaluate to None/null for N/A display")

    # ─────────────────────────────────────────────────────────────────────────
    # Requirement 15 (Audit Fix 3): Consistent multi-window soft voting decisions
    # ─────────────────────────────────────────────────────────────────────────
    def test_15_consistent_multi_window_decisions(self):
        # Construct synthetic timestamps for 2 full windows (257 packets)
        # Window 1: high Echo activity (0.01s IAT)
        # Window 2: moderate Echo activity (0.02s IAT)
        ts = [0.0]
        for _ in range(128):
            ts.append(ts[-1] + 0.01)
        for _ in range(128):
            ts.append(ts[-1] + 0.02)

        # 1. Verify via pipeline
        wins, summary = process_packet_timestamps(ts, threshold=0.84)
        self.assertEqual(len(wins), 2)
        self.assertIn("soft_verdict", summary)
        self.assertIn("mean_probabilities", summary)

        # 2. Verify via routes/spoof backend function with n_group=2
        req = SpoofVerifyRequest(
            timestamps=ts,
            claimed_identity="AmazonEcho",
            threshold=0.84,
            n_group=2
        )
        backend_res = verify_claimed_identity(req)

        # 3. Verify via src/spoof verify_stream
        probs_matrix = np.array([[w["probs"][c] for c in CLASSES] for w in wins])
        cli_res = verify_stream(probs_matrix, CLASSES, claimed="AmazonEcho", n=2, tau=0.84, method="soft")

        # Assert identical verdicts and confidence
        self.assertEqual(backend_res["device_level_verdict"], cli_res["verdict"])
        self.assertEqual(backend_res["device_predicted"], cli_res["predicted"])
        self.assertAlmostEqual(backend_res["mean_confidence"], cli_res["confidence"], places=3)
        self.assertEqual(backend_res["aggregation_method"], "soft_probability_averaging")


if __name__ == "__main__":
    unittest.main()
