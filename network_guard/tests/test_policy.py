"""
Unit tests for the pure response policy engine.
"""

import pytest
from network_guard.backend.policy import (
    evaluate_policy,
    ACTION_ALLOW,
    ACTION_QUARANTINE,
    ACTION_ISOLATE,
    ACTION_OBSERVE
)

def test_verified_policy():
    res = evaluate_policy("VERIFIED")
    assert res["action"] == ACTION_ALLOW
    assert res["alert"] is False
    assert "access granted" in res["description"].lower()

def test_spoof_suspected_policy():
    res = evaluate_policy("SPOOF_SUSPECTED")
    assert res["action"] == ACTION_QUARANTINE
    assert res["alert"] is True
    assert "quarantined" in res["description"].lower()

def test_unknown_hardware_policy():
    res = evaluate_policy("UNKNOWN_HARDWARE")
    assert res["action"] == ACTION_ISOLATE
    assert res["alert"] is True
    assert "vlan 99" in res["description"].lower()

def test_insufficient_data_policy():
    res = evaluate_policy("INSUFFICIENT_DATA")
    assert res["action"] == ACTION_OBSERVE
    assert res["alert"] is False
    assert "observation" in res["description"].lower()

def test_unrecognized_verdict_fallback():
    res = evaluate_policy("SOME_UNKNOWN_VERDICT")
    assert res["action"] == ACTION_ISOLATE
    assert res["alert"] is True
