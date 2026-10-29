"""
Unit tests for the HostStateMachine and multi-window aggregation.
Tests hysteresis transitions and INSUFFICIENT_DATA state handling.
"""

import pytest
from network_guard.backend.state_machine import (
    HostStateMachine,
    STATE_OBSERVING,
    STATE_TRUSTED,
    STATE_QUARANTINED,
    STATE_ISOLATED
)
from network_guard.backend.policy import (
    ACTION_ALLOW,
    ACTION_QUARANTINE,
    ACTION_ISOLATE,
    ACTION_OBSERVE
)
from network_guard.backend.model_loader import ModelManager


def test_state_machine_initial_state():
    sm = HostStateMachine("test-host", "AmazonEcho", "192.168.1.101", "44:65:0D:56:CC:D3", hysteresis=2)
    assert sm.current_state == STATE_OBSERVING
    assert sm.firewall_rules["action"] == ACTION_OBSERVE


def test_hysteresis_trusted_transition():
    sm = HostStateMachine("test-host", "AmazonEcho", "192.168.1.101", "44:65:0D:56:CC:D3", hysteresis=2)

    # 1st VERIFIED verdict: should remain OBSERVING (hysteresis pending count = 1)
    res1 = sm.update("VERIFIED", confidence=0.95, predicted_device="AmazonEcho")
    assert res1["current_state"] == STATE_OBSERVING
    assert res1["transitioned"] is False
    assert sm.pending_count == 1

    # 2nd consecutive VERIFIED verdict: should transition to TRUSTED
    res2 = sm.update("VERIFIED", confidence=0.96, predicted_device="AmazonEcho")
    assert res2["current_state"] == STATE_TRUSTED
    assert res2["transitioned"] is True
    assert res2["action"] == ACTION_ALLOW


def test_hysteresis_quarantine_transition():
    sm = HostStateMachine("test-host", "AmazonEcho", "192.168.1.101", "44:65:0D:56:CC:D3", hysteresis=2)

    # Reach trusted
    sm.update("VERIFIED")
    sm.update("VERIFIED")
    assert sm.current_state == STATE_TRUSTED

    # 1st SPOOF_SUSPECTED verdict: remains TRUSTED
    res1 = sm.update("SPOOF_SUSPECTED", confidence=0.92, predicted_device="SamsungCamera")
    assert res1["current_state"] == STATE_TRUSTED
    assert res1["transitioned"] is False
    assert sm.pending_count == 1

    # 2nd consecutive SPOOF_SUSPECTED verdict: transitions to QUARANTINED
    res2 = sm.update("SPOOF_SUSPECTED", confidence=0.94, predicted_device="SamsungCamera")
    assert res2["current_state"] == STATE_QUARANTINED
    assert res2["transitioned"] is True
    assert res2["action"] == ACTION_QUARANTINE
    assert res2["alert"] is True


def test_hysteresis_isolation_transition():
    sm = HostStateMachine("test-host", "AmazonEcho", "192.168.1.101", "44:65:0D:56:CC:D3", hysteresis=2)

    # 2 consecutive UNKNOWN_HARDWARE verdicts
    sm.update("UNKNOWN_HARDWARE", confidence=0.45)
    assert sm.current_state == STATE_OBSERVING

    res = sm.update("UNKNOWN_HARDWARE", confidence=0.50)
    assert res["current_state"] == STATE_ISOLATED
    assert res["action"] == ACTION_ISOLATE
    assert res["alert"] is True


def test_insufficient_data_does_not_trigger_transition():
    sm = HostStateMachine("test-host", "AmazonEcho", "192.168.1.101", "44:65:0D:56:CC:D3", hysteresis=2)

    res = sm.update("INSUFFICIENT_DATA")
    assert res["current_state"] == STATE_OBSERVING
    assert res["action"] == ACTION_OBSERVE
    assert sm.pending_verdict is None
    assert sm.pending_count == 0


def test_five_window_aggregation():
    mm = ModelManager.get_instance()
    
    # 3 windows (fewer than n=5)
    sample_windows = [
        {"probabilities": {c: 0.9 if c == "AmazonEcho" else 0.025 for c in mm.classes}}
        for _ in range(3)
    ]
    dev_res = mm.compute_device_verdict(sample_windows, claimed_device="AmazonEcho", n_windows=5)
    assert dev_res["verdict"] == "INSUFFICIENT_DATA"
    assert dev_res["window_count"] == 3

    # Add 2 more windows to make 5
    sample_windows.extend([
        {"probabilities": {c: 0.95 if c == "AmazonEcho" else 0.0125 for c in mm.classes}},
        {"probabilities": {c: 0.92 if c == "AmazonEcho" else 0.02 for c in mm.classes}}
    ])
    dev_res2 = mm.compute_device_verdict(sample_windows, claimed_device="AmazonEcho", n_windows=5)
    assert dev_res2["verdict"] == "VERIFIED"
    assert dev_res2["window_count"] == 5
    assert dev_res2["confidence"] > 0.84

