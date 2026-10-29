"""
Per-Host Defense State Machine with Hysteresis
"""
from typing import Dict, Any, List, Optional
import numpy as np
from network_guard.backend.policy import decide_action, generate_firewall_rules


class HostStateMachine:
    """
    Manages the lifecycle and state transitions for a single host.
    States:
      OBSERVING   - Gathering initial observation windows (fewer than N windows)
      TRUSTED     - Timing behavior verified to match registered identity
      QUARANTINED - Timing behavior indicates identity spoofing / MAC impersonation
      ISOLATED    - Timing behavior does not match any known profile (foreign hardware)
    """

    def __init__(
        self,
        host_id: str,
        name: str,
        ip: str,
        mac: str,
        claimed_device: str,
        hysteresis_count: int = 2,
        window_buffer_size: int = 5,
    ):
        self.host_id = host_id
        self.name = name
        self.ip = ip
        self.mac = mac
        self.claimed_device = claimed_device
        self.hysteresis_threshold = hysteresis_count
        self.window_buffer_size = window_buffer_size

        # State tracking
        self.state = "OBSERVING"
        self.pending_state: Optional[str] = None
        self.pending_count: int = 0

        # Windows and probability history
        self.probabilities_history: List[np.ndarray] = []
        self.recent_iats: List[float] = []  # For sparkline display
        self.window_verdicts_history: List[str] = []
        self.device_verdicts_history: List[str] = []
        self.state_history: List[Dict[str, Any]] = [
            {"state": "OBSERVING", "tick": 0, "reason": "Initial state"}
        ]
        self.active_rule = generate_firewall_rules(self.ip, self.mac, "OBSERVE")

        # Latest stats for UI rendering
        self.latest_window_verdict = "INSUFFICIENT_DATA"
        self.latest_device_verdict = "INSUFFICIENT_DATA"
        self.latest_confidence = 0.0
        self.latest_predicted_class = claimed_device
        self.latest_class_probabilities: Dict[str, float] = {}
        self.total_windows_processed = 0
        self.time_in_state = {"OBSERVING": 0, "TRUSTED": 0, "QUARANTINED": 0, "ISOLATED": 0}

    def process_window(
        self,
        prob_vector: np.ndarray,
        classes: List[str],
        window_verdict: str,
        device_verdict_info: Dict[str, Any],
        raw_iats: Optional[List[float]] = None,
        tick: int = 0,
    ) -> Dict[str, Any]:
        """
        Ingest a new 128-packet window result, update hysteresis, and evaluate state transitions.
        """
        self.total_windows_processed += 1
        self.time_in_state[self.state] = self.time_in_state.get(self.state, 0) + 1

        self.probabilities_history.append(prob_vector)
        self.window_verdicts_history.append(window_verdict)
        self.latest_window_verdict = window_verdict

        if raw_iats is not None and len(raw_iats) > 0:
            # Keep sample for sparkline visualization (subsample or last 32 points)
            self.recent_iats = list(raw_iats[-32:])

        # Unpack device verdict info
        device_verdict = device_verdict_info.get("verdict", "INSUFFICIENT_DATA")
        self.latest_device_verdict = device_verdict
        self.device_verdicts_history.append(device_verdict)

        top_prob = float(np.max(prob_vector))
        top_idx = int(np.argmax(prob_vector))
        self.latest_confidence = round(float(device_verdict_info.get("confidence", top_prob)), 4)
        self.latest_predicted_class = str(device_verdict_info.get("predicted", classes[top_idx]))

        # Format probability distribution
        if "mean_probabilities" in device_verdict_info:
            self.latest_class_probabilities = {
                k: round(float(v), 4) for k, v in device_verdict_info["mean_probabilities"].items()
            }
        else:
            self.latest_class_probabilities = {
                c: round(float(p), 4) for c, p in zip(classes, prob_vector)
            }

        # Policy decision based on device-level aggregate verdict
        policy = decide_action(device_verdict)
        target_state = policy["target_state"]

        transition_occurred = False
        previous_state = self.state

        # Hysteresis state transition logic
        if target_state == self.state:
            # Already in target state; reset pending transition
            self.pending_state = None
            self.pending_count = 0
        else:
            if target_state == self.pending_state:
                self.pending_count += 1
            else:
                self.pending_state = target_state
                self.pending_count = 1

            if self.pending_count >= self.hysteresis_threshold:
                # Transition confirmed by hysteresis
                self.state = target_state
                transition_occurred = True
                self.state_history.append({
                    "from_state": previous_state,
                    "to_state": self.state,
                    "tick": tick,
                    "trigger_verdict": device_verdict,
                    "reason": policy["description"],
                })
                # Update text firewall rules
                self.active_rule = generate_firewall_rules(self.ip, self.mac, policy["action"])
                self.pending_state = None
                self.pending_count = 0

        return {
            "host_id": self.host_id,
            "ip": self.ip,
            "mac": self.mac,
            "state": self.state,
            "previous_state": previous_state,
            "transition": transition_occurred,
            "window_verdict": window_verdict,
            "device_verdict": device_verdict,
            "confidence": self.latest_confidence,
            "predicted": self.latest_predicted_class,
            "claimed": self.claimed_device,
            "action": policy["action"],
            "alert": policy["alert"],
            "rule": self.active_rule,
            "policy": policy,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize host state for REST and WebSocket responses."""
        policy = decide_action(self.latest_device_verdict)
        return {
            "id": self.host_id,
            "name": self.name,
            "ip": self.ip,
            "mac": self.mac,
            "claimed_device": self.claimed_device,
            "state": self.state,
            "pending_state": self.pending_state,
            "pending_count": self.pending_count,
            "latest_window_verdict": self.latest_window_verdict,
            "latest_device_verdict": self.latest_device_verdict,
            "confidence": self.latest_confidence,
            "predicted": self.latest_predicted_class,
            "probabilities": self.latest_class_probabilities,
            "total_windows": self.total_windows_processed,
            "time_in_state": self.time_in_state,
            "recent_iats": self.recent_iats,
            "action": policy["action"],
            "severity": policy["severity"],
            "alert": policy["alert"],
            "active_rule": self.active_rule,
        }

