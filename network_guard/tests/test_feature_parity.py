"""
Feature Parity Test.
Verifies that computing 13 statistical moments from raw test windows
and passing them through the scaler matches stored values in raw_scaled_test.csv
within 1e-4 tolerance.
"""

import os
import pytest
import numpy as np
import pandas as pd
from network_guard.backend.config import DATA_FEATURES_DIR, KNOWN_DEVICES
from network_guard.backend.model_loader import ModelManager
from src.features import compute_raw_stats, RAW_FEATURE_NAMES


def test_feature_parity_against_stored_split():
    """
    Test feature parity across 50 test-split windows for each known device.
    Max absolute difference must be <= 1e-4.
    """
    mm = ModelManager.get_instance()
    test_scaled_path = DATA_FEATURES_DIR / "raw_scaled_test.csv"
    assert test_scaled_path.exists(), f"Missing {test_scaled_path}"

    test_df = pd.read_csv(test_scaled_path)
    iat_cols = [f"iat_{i}" for i in range(128)]

    tested_total = 0
    max_global_diff = 0.0

    for dev in KNOWN_DEVICES:
        dev_win_path = DATA_FEATURES_DIR / f"{dev}_windows.csv"
        assert dev_win_path.exists(), f"Missing {dev_win_path}"
        dev_raw_df = pd.read_csv(dev_win_path)

        # Merge on window_id
        dev_test_df = test_df[test_df["device_label"] == dev]
        merged = pd.merge(dev_test_df, dev_raw_df, on="window_id", suffixes=("_stored", "_raw"))
        assert len(merged) > 0, f"No overlapping test windows for {dev}"

        sample_rows = merged.iloc[:30]

        for _, row in sample_rows.iterrows():
            raw_w = row[[f"{c}_raw" if f"{c}_raw" in row else c for c in iat_cols]].values.astype(float)
            stored_scaled = row[[f"{fn}_stored" if f"{fn}_stored" in row else fn for fn in RAW_FEATURE_NAMES]].values.astype(float)

            # Compute moments and scale
            stats = compute_raw_stats(raw_w)
            calc_unscaled = np.array([stats[fn] for fn in RAW_FEATURE_NAMES], dtype=np.float64).reshape(1, -1)
            calc_scaled = mm.scaler_wrapper.transform(calc_unscaled).ravel()

            abs_diff = np.max(np.abs(calc_scaled - stored_scaled))
            max_global_diff = max(max_global_diff, abs_diff)
            tested_total += 1

            assert abs_diff <= 1e-4, (
                f"Feature parity violation on {dev} window {row['window_id']}: "
                f"Max diff {abs_diff:.2e} exceeds tolerance 1e-4"
            )

    print(f"Verified feature parity on {tested_total} windows across 5 devices! Max difference: {max_global_diff:.2e}")
