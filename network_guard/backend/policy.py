"""
Response policy engine for Network Defense Lab.
Pure function with zero side effects.
"""

from typing import Dict, Any, Tuple

ACTION_ALLOW = "ALLOW"
ACTION_QUARANTINE = "QUARANTINE"
ACTION_ISOLATE = "ISOLATE"
ACTION_OBSERVE = "OBSERVE"

POLICY_MAP = {
    "VERIFIED": {
        "action": ACTION_ALLOW,
        "alert": False,
        "description": "Timing profile matches claimed identity above threshold. Full LAN access granted."
    },
    "SPOOF_SUSPECTED": {
        "action": ACTION_QUARANTINE,
        "alert": True,
        "description": "High-confidence timing mismatch with claimed identity. Host quarantined for investigation."
    },
    "UNKNOWN_HARDWARE": {
        "action": ACTION_ISOLATE,
        "alert": True,
        "description": "Traffic confidence below threshold tau. Host moved to isolated containment VLAN 99."
    },
    "INSUFFICIENT_DATA": {
        "action": ACTION_OBSERVE,
        "alert": False,
        "description": "Fewer than n=5 timing windows collected. Rate-limited observation active."
    }
}

def evaluate_policy(verdict: str) -> Dict[str, Any]:
    """
    Pure function: maps a device-level or window-level verdict to a response policy.

    Args:
        verdict: One of 'VERIFIED', 'SPOOF_SUSPECTED', 'UNKNOWN_HARDWARE', 'INSUFFICIENT_DATA'

    Returns:
        Dict with keys: action, alert, description
    """
    if verdict not in POLICY_MAP:
        # Fallback to safest action
        return {
            "action": ACTION_ISOLATE,
            "alert": True,
            "description": f"Unrecognized verdict '{verdict}'. Safe isolation fallback applied."
        }
    return dict(POLICY_MAP[verdict])

