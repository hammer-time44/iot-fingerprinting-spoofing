"""
Host State Machine with Hysteresis for Network Defense Lab.
Tracks per-host security states: OBSERVING, TRUSTED, QUARANTINED, ISOLATED.
"""

from typing import List, Optional, Dict, Any
from .policy import evaluate_policy, ACTION_ALLOW, ACTION_QUARANTINE, ACTION_ISOLATE, ACTION_OBSERVE
from .firewall import generate_firewall_rules

STATE_OBSERVING = "OBSERVING"
STATE_TRUSTED = "TRUSTED"
STATE_QUARANTINED = "QUARANTINED"
STATE_ISOLATED = "ISOLATED"

VERDICT_TO_STATE = {
    "VERIFIED": STATE_TRUSTED,
    "SPOOF_SUSPECTED": STATE_QUARANTINED,
    "UNKNOWN_HARDWARE": STATE_ISOLATED
}

class HostStateMachine:
    def __init__(
        self,
        host_id: str,
        claimed_device: str,
        ip: str,
        mac: str,
        hysteresis: int = 2
    ):
        self.host_id = host_id
        self.claimed_device = claimed_device
        self.ip = ip
        self.mac = mac
        self.hysteresis = hysteresis

        self.current_state: str = STATE_OBSERVING
        self.verdict_history: List[str] = []
        self.state_history: List[str] = [STATE_OBSERVING]
        self.pending_verdict: Optional[str] = None
        self.pending_count: int = 0
        self.firewall_rules: Dict[str, str] = generate_firewall_rules(
            ACTION_OBSERVE, ip=self.ip, mac=self.mac, claimed_device=self.claimed_device
        )
        self.time_in_states: Dict[str, int] = {
            STATE_OBSERVING: 0,
            STATE_TRUSTED: 0,
            STATE_QUARANTINED: 0,
            STATE_ISOLATED: 0
        }

    def update(
        self,
        device_level_verdict: str,
        confidence: float = 0.0,
        predicted_device: str = ""
    ) -> Dict[str, Any]:
        """
        Update the host state machine with a new device-level verdict.

        Args:
            device_level_verdict: 'VERIFIED', 'SPOOF_SUSPECTED', 'UNKNOWN_HARDWARE', 'INSUFFICIENT_DATA'
            confidence: Model confidence
            predicted_device: Top predicted device profile

        Returns:
            Dict containing current state, action, rule text, alert, and transition details.
        """
        self.time_in_states[self.current_state] += 1
        self.verdict_history.append(device_level_verdict)
        transitioned = False
        previous_state = self.current_state

        if device_level_verdict in VERDICT_TO_STATE:
            target_state = VERDICT_TO_STATE[device_level_verdict]
            
            # Check if this verdict matches the pending verdict counter
            if self.pending_verdict == target_state:
                self.pending_count += 1
            else:
                self.pending_verdict = target_state
                self.pending_count = 1

            # Hysteresis check: transition only if pending count reaches threshold
            if self.pending_count >= self.hysteresis:
                if self.current_state != target_state:
                    self.current_state = target_state
                    transitioned = True
                    self.state_history.append(target_state)
        else:
            # For INSUFFICIENT_DATA or unrecognized, reset pending counter
            self.pending_verdict = None
            self.pending_count = 0

        # Evaluate policy corresponding to current state
        if self.current_state == STATE_TRUSTED:
            action = ACTION_ALLOW
            alert = False
        elif self.current_state == STATE_QUARANTINED:
            action = ACTION_QUARANTINE
            alert = True
        elif self.current_state == STATE_ISOLATED:
            action = ACTION_ISOLATE
            alert = True
        else:
            action = ACTION_OBSERVE
            alert = False

        self.firewall_rules = generate_firewall_rules(
            action=action,
            ip=self.ip,
            mac=self.mac,
            claimed_device=self.claimed_device,
            target_device=predicted_device,
            confidence=confidence
        )

        return {
            "host_id": self.host_id,
            "current_state": self.current_state,
            "previous_state": previous_state,
            "transitioned": transitioned,
            "action": action,
            "alert": alert,
            "pending_verdict": self.pending_verdict,
            "pending_count": self.pending_count,
            "firewall_rules": self.firewall_rules
        }

    def reset(self):
        """Reset state machine to initial observing state."""
        self.current_state = STATE_OBSERVING
        self.verdict_history.clear()
        self.state_history = [STATE_OBSERVING]
        self.pending_verdict = None
        self.pending_count = 0
        self.firewall_rules = generate_firewall_rules(
            ACTION_OBSERVE, ip=self.ip, mac=self.mac, claimed_device=self.claimed_device
        )
        self.time_in_states = {
            STATE_OBSERVING: 0,
            STATE_TRUSTED: 0,
            STATE_QUARANTINED: 0,
            STATE_ISOLATED: 0
        }

