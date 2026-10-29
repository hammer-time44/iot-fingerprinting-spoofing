"""
Parity test comparing ModelManager verdict logic with src.spoof.verdicts()
over 1,000 randomly generated probability distributions.
"""

import numpy as np
import pytest
from network_guard.backend.model_loader import ModelManager
from src.spoof import verdicts as spoof_verdicts


def test_verdict_parity_1000_matrices():
    """
    Generate 1,000 random Dirichlet probability distributions across the 5 known classes
    and test exact verdict parity between ModelManager and src.spoof.verdicts().
    """
    mm = ModelManager.get_instance()
    classes = mm.classes
    n_classes = len(classes)
    rng = np.random.default_rng(12345)
    
    # Generate 1,000 probability vectors with varied Dirichlet concentration
    # to test both confident distributions and diffuse/uncertain distributions
    alphas = [0.1, 0.5, 1.0, 5.0]
    tau_vals = [0.50, 0.70, 0.84, 0.90]

    for trial in range(1000):
        alpha = rng.choice(alphas)
        tau = float(rng.choice(tau_vals))
        claimed_device = str(rng.choice(classes))

        P = rng.dirichlet(np.ones(n_classes) * alpha).reshape(1, -1)

        # 1. Output from ModelManager
        mm_res = mm.score_probabilities(P, claimed_device=claimed_device, tau=tau)[0]
        mm_verdict = mm_res["verdict"]

        # 2. Output from authoritative src.spoof.verdicts
        sp_arr = spoof_verdicts(P, classes, claimed=claimed_device, tau=tau)
        sp_verdict = str(sp_arr[0])

        assert mm_verdict == sp_verdict, (
            f"Parity mismatch at trial {trial}!\n"
            f"P={P.ravel()}, Claimed={claimed_device}, Tau={tau}\n"
            f"ModelManager={mm_verdict} vs src.spoof={sp_verdict}"
        )

    print("Successfully verified 1,000/1,000 random probability matrices with exact parity!")
