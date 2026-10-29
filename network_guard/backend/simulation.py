"""
Simulation Engine for Network Defense Lab.
Manages simulated clock, network topology, legitimate host traffic replay,
attacker scenario traffic generation, state machines, and event dispatch.
"""

import time
import copy
import numpy as np
from typing import Dict, List, Any, Optional

from .config import (
    REGISTERED_HOSTS,
    GATEWAY_INFO,
    KNOWN_DEVICES,
    DEFAULT_TAU,
    DEFAULT_HYSTERESIS,
    DEFAULT_AGG_WINDOW_COUNT
)
from .model_loader import ModelManager
from .state_machine import HostStateMachine
from .firewall import generate_firewall_rules
from src.spoof_eval import quantile_map, apply_jitter


class SimulationEngine:
    def __init__(self, seed: int = 42, tau: float = DEFAULT_TAU):
        self.seed = seed
        self.tau = tau
        self.rng = np.random.default_rng(seed)
        self.model_manager = ModelManager.get_instance()
        self.model_manager.tau = tau

        # Simulation clock and control
        self.tick_count: int = 0
        self.is_running: bool = False
        self.speed: float = 1.0  # 1.0 tick/sec base
        self.hysteresis: int = DEFAULT_HYSTERESIS
        self.agg_window_count: int = DEFAULT_AGG_WINDOW_COUNT

        # Active Scenario Config
        self.active_scenario: str = "BASELINE"
        self.scenario_params: Dict[str, Any] = {}

        # Hosts and State Machines
        self.hosts: Dict[str, Dict[str, Any]] = {}
        self.state_machines: Dict[str, HostStateMachine] = {}
        
        # Window pointer per host (to cycle through test split)
        self.window_indices: Dict[str, int] = {}
        
        # Per-host window history buffer (for 5-window aggregation and sparklines)
        self.window_history: Dict[str, List[Dict[str, Any]]] = {}
        self.sparkline_history: Dict[str, List[float]] = {}

        # Metrics and Events
        self.events: List[Dict[str, Any]] = []
        self.scenario_metrics: Dict[str, Any] = {}

        self.reset()

    def reset(self):
        """Reset the simulation environment, state machines, and topologies."""
        self.tick_count = 0
        self.is_running = False
        self.rng = np.random.default_rng(self.seed)
        self.events.clear()

        # Initialize Home LAN hosts
        self.hosts.clear()
        self.state_machines.clear()
        self.window_indices.clear()
        self.window_history.clear()
        self.sparkline_history.clear()

        for host_id, hinfo in REGISTERED_HOSTS.items():
            self.hosts[host_id] = copy.deepcopy(hinfo)
            self.hosts[host_id]["is_attacker"] = False
            self.hosts[host_id]["current_state"] = "OBSERVING"
            self.hosts[host_id]["window_verdict"] = None
            self.hosts[host_id]["device_verdict"] = "INSUFFICIENT_DATA"
            self.hosts[host_id]["confidence"] = 0.0
            self.hosts[host_id]["probabilities"] = {dev: 0.0 for dev in KNOWN_DEVICES}
            self.hosts[host_id]["firewall_action"] = "OBSERVE"

            sm = HostStateMachine(
                host_id=host_id,
                claimed_device=hinfo["claimed_device"],
                ip=hinfo["ip"],
                mac=hinfo["mac"],
                hysteresis=self.hysteresis
            )
            self.state_machines[host_id] = sm
            self.window_indices[host_id] = 0
            self.window_history[host_id] = []
            self.sparkline_history[host_id] = []

        self.scenario_metrics = {
            "first_detection_tick": None,
            "detected": False,
            "false_alarms": 0,
            "total_windows_evaluated": 0
        }

    def set_tau(self, tau: float):
        """Update confidence threshold tau dynamically."""
        self.tau = float(tau)
        self.model_manager.tau = self.tau

    def configure_scenario(self, scenario: str, params: Optional[Dict[str, Any]] = None):
        """
        Configure a simulation scenario.
        Scenarios:
          1. 'BASELINE' - Legitimate Home LAN only
          2. 'IMPERSONATION' - Rogue claims Y, sends X
          3. 'UNKNOWN_HARDWARE' - Rogue claims Y, sends unseen UNSW device
          4. 'TIMING_MIMICRY' - Rogue quantile-mapped to target
          5. 'HIJACKED_DEVICE' - Registered host transitions to foreign timing mid-run
          6. 'REPLAY' - Rogue replays target recorded windows (blind spot demo)
          7. 'ACCESS_ATTEMPT' - Attacker network tries connection; gateway default-deny demo
        """
        self.reset()
        self.active_scenario = scenario
        self.scenario_params = params or {}

        # Default params
        if scenario == "IMPERSONATION":
            self.scenario_params.setdefault("source_device", "SamsungCamera")
            self.scenario_params.setdefault("claimed_device", "AmazonEcho")
            self._inject_attacker_host(
                claimed_device=self.scenario_params["claimed_device"],
                source_device=self.scenario_params["source_device"],
                label="Rogue Spoofing Device"
            )

        elif scenario == "UNKNOWN_HARDWARE":
            unk_choices = self.model_manager.unknown_device_names
            default_unk = "WithingsSmartScale" if "WithingsSmartScale" in unk_choices else (unk_choices[0] if unk_choices else "ForeignDevice")
            self.scenario_params.setdefault("unseen_device", default_unk)
            self.scenario_params.setdefault("claimed_device", "AmazonEcho")
            self._inject_attacker_host(
                claimed_device=self.scenario_params["claimed_device"],
                source_device=self.scenario_params["unseen_device"],
                label=f"Foreign Hardware ({self.scenario_params['unseen_device']})",
                is_unknown_hardware=True
            )

        elif scenario == "TIMING_MIMICRY":
            self.scenario_params.setdefault("source_device", "SamsungCamera")
            self.scenario_params.setdefault("target_device", "AmazonEcho")
            self.scenario_params.setdefault("strength", 0.6)
            self.scenario_params.setdefault("apply_jitter", False)
            
            src_dev = self.scenario_params["source_device"]
            tgt_dev = self.scenario_params["target_device"]
            strength = float(self.scenario_params["strength"])
            src_pool = self.model_manager.test_windows_by_device[src_dev]
            tgt_pool = self.model_manager.test_windows_by_device[tgt_dev]

            # Vectorized precomputation of mimicry pool for this scenario run
            self._mimicry_window_pool = quantile_map(src_pool, tgt_pool.ravel(), strength)
            if self.scenario_params.get("apply_jitter", False):
                self._mimicry_window_pool = apply_jitter(self._mimicry_window_pool, strength, self.rng)

            self._inject_attacker_host(
                claimed_device=self.scenario_params["target_device"],
                source_device=self.scenario_params["source_device"],
                label=f"Timing Mimicry Attacker (s={strength:.2f})"
            )

        elif scenario == "HIJACKED_DEVICE":
            self.scenario_params.setdefault("target_host", "host-echo")
            self.scenario_params.setdefault("hijack_at_tick", 6)
            self.scenario_params.setdefault("hijack_device", "SamsungCamera")

        elif scenario == "REPLAY":
            self.scenario_params.setdefault("target_device", "AmazonEcho")
            self._inject_attacker_host(
                claimed_device=self.scenario_params["target_device"],
                source_device=self.scenario_params["target_device"],
                label="Replay Attacker (Exact Recorded Windows)"
            )

        elif scenario == "ACCESS_ATTEMPT":
            self.scenario_params.setdefault("target_ip", "192.168.1.101")
            self.scenario_params.setdefault("port", 443)
            self._inject_attacker_host(
                claimed_device="UnknownClient",
                source_device="AmazonEcho",
                ip="10.0.0.99",
                label="External Attacker (Port Scan / Exploit Probe)"
            )

    def _inject_attacker_host(
        self,
        claimed_device: str,
        source_device: str,
        label: str = "Attacker Host",
        ip: str = "10.0.0.66",
        mac: str = "B8:27:EB:AA:BB:CC",
        is_unknown_hardware: bool = False
    ):
        """Add an attacker host to the topology."""
        attacker_id = "host-attacker"
        self.hosts[attacker_id] = {
            "id": attacker_id,
            "name": label,
            "claimed_device": claimed_device,
            "source_device": source_device,
            "mac": mac,
            "ip": ip,
            "network": "ATTACKER_NET",
            "icon": "Skull",
            "is_attacker": True,
            "is_unknown_hardware": is_unknown_hardware,
            "current_state": "OBSERVING",
            "window_verdict": None,
            "device_verdict": "INSUFFICIENT_DATA",
            "confidence": 0.0,
            "probabilities": {dev: 0.0 for dev in KNOWN_DEVICES},
            "firewall_action": "OBSERVE"
        }
        self.state_machines[attacker_id] = HostStateMachine(
            host_id=attacker_id,
            claimed_device=claimed_device,
            ip=ip,
            mac=mac,
            hysteresis=self.hysteresis
        )
        self.window_indices[attacker_id] = 0
        self.window_history[attacker_id] = []
        self.sparkline_history[attacker_id] = []

    def _get_next_window_for_host(self, host_id: str) -> np.ndarray:
        """Fetch the next 128-element log1p(IAT) window for a given host."""
        hinfo = self.hosts[host_id]
        
        # Check for Hijacked Device scenario
        if self.active_scenario == "HIJACKED_DEVICE":
            if host_id == self.scenario_params.get("target_host"):
                hijack_tick = self.scenario_params.get("hijack_at_tick", 6)
                if self.tick_count >= hijack_tick:
                    hijack_device = self.scenario_params.get("hijack_device", "SamsungCamera")
                    pool = self.model_manager.test_windows_by_device.get(hijack_device)
                    idx = self.window_indices[host_id] % len(pool)
                    self.window_indices[host_id] += 1
                    return pool[idx]

        # Check for Attacker Host
        if hinfo.get("is_attacker"):
            if self.active_scenario == "UNKNOWN_HARDWARE":
                unk_dev = hinfo.get("source_device")
                pool = self.model_manager.unknown_windows_by_device.get(unk_dev)
                if pool is None or len(pool) == 0:
                    # fallback to any available unknown device
                    pool = list(self.model_manager.unknown_windows_by_device.values())[0]
                idx = self.window_indices[host_id] % len(pool)
                self.window_indices[host_id] += 1
                return pool[idx]

            elif self.active_scenario == "TIMING_MIMICRY":
                pool = getattr(self, "_mimicry_window_pool", None)
                if pool is None or len(pool) == 0:
                    src_dev = self.scenario_params.get("source_device", "SamsungCamera")
                    pool = self.model_manager.test_windows_by_device[src_dev]
                idx = self.window_indices[host_id] % len(pool)
                self.window_indices[host_id] += 1
                return pool[idx]

            elif self.active_scenario in ["IMPERSONATION", "REPLAY"]:
                src_dev = hinfo.get("source_device")
                pool = self.model_manager.test_windows_by_device[src_dev]
                idx = self.window_indices[host_id] % len(pool)
                self.window_indices[host_id] += 1
                return pool[idx]

        # Standard Legitimate Host: replay its own test windows
        claimed = hinfo["claimed_device"]
        pool = self.model_manager.test_windows_by_device.get(claimed)
        if pool is None or len(pool) == 0:
            raise RuntimeError(f"No test windows available for legitimate host {claimed}")
        
        idx = self.window_indices[host_id] % len(pool)
        self.window_indices[host_id] += 1
        return pool[idx]

    def tick(self) -> Dict[str, Any]:
        """
        Advance simulation by one clock tick.
        Evaluates one 128-value timing window per active host.
        Updates state machines, evaluates response policies, and logs events.
        """
        self.tick_count += 1
        tick_events = []
        host_updates = {}

        # Handle Policy Demo Scenario: ACCESS_ATTEMPT
        if self.active_scenario == "ACCESS_ATTEMPT":
            rule_text = (
                f"# [SIMULATION TEXT ONLY] Gateway Default-Deny Policy\n"
                f"iptables -A FORWARD -s 10.0.0.99 -d {self.scenario_params.get('target_ip', '192.168.1.101')} "
                f"-p tcp --dport {self.scenario_params.get('port', 443)} -j DROP"
            )
            event = {
                "tick": self.tick_count,
                "timestamp": time.strftime("%H:%M:%S"),
                "event_type": "FIREWALL_POLICY_DENY",
                "host_id": "host-attacker",
                "source_ip": "10.0.0.99",
                "target_ip": self.scenario_params.get("target_ip", "192.168.1.101"),
                "port": self.scenario_params.get("port", 443),
                "verdict": "POLICY_BLOCKED",
                "action": "DROP",
                "description": "Gateway firewall default-deny dropped external connection attempt from attacker network.",
                "rule_text": rule_text
            }
            self.events.append(event)
            tick_events.append(event)
            self.scenario_metrics["detected"] = True
            if self.scenario_metrics["first_detection_tick"] is None:
                self.scenario_metrics["first_detection_tick"] = self.tick_count

        # Process timing pipeline for each active host
        for host_id, hinfo in self.hosts.items():
            claimed = hinfo["claimed_device"]
            
            # Check if this is a standard known or unknown device without dynamic noise
            use_fast_cache = False
            cached_probs = None
            window_raw = None

            if not hinfo.get("is_attacker"):
                if self.active_scenario == "HIJACKED_DEVICE" and host_id == self.scenario_params.get("target_host"):
                    hijack_tick = self.scenario_params.get("hijack_at_tick", 6)
                    if self.tick_count >= hijack_tick:
                        hijack_device = self.scenario_params.get("hijack_device", "SamsungCamera")
                        pool = self.model_manager.test_windows_by_device.get(hijack_device)
                        idx = self.window_indices[host_id] % len(pool)
                        self.window_indices[host_id] += 1
                        window_raw = pool[idx]
                        cached_probs = self.model_manager.get_device_test_probs(hijack_device)[idx]
                        use_fast_cache = True
                if not use_fast_cache:
                    pool = self.model_manager.test_windows_by_device.get(claimed)
                    idx = self.window_indices[host_id] % len(pool)
                    self.window_indices[host_id] += 1
                    window_raw = pool[idx]
                    cached_probs = self.model_manager.get_device_test_probs(claimed)[idx]
                    use_fast_cache = True
            else:
                if self.active_scenario in ["IMPERSONATION", "REPLAY"]:
                    src_dev = hinfo.get("source_device")
                    pool = self.model_manager.test_windows_by_device.get(src_dev)
                    idx = self.window_indices[host_id] % len(pool)
                    self.window_indices[host_id] += 1
                    window_raw = pool[idx]
                    cached_probs = self.model_manager.get_device_test_probs(src_dev)[idx]
                    use_fast_cache = True
                elif self.active_scenario == "UNKNOWN_HARDWARE":
                    unk_dev = hinfo.get("source_device")
                    pool = self.model_manager.unknown_windows_by_device.get(unk_dev)
                    if pool is not None and len(pool) > 0:
                        idx = self.window_indices[host_id] % len(pool)
                        self.window_indices[host_id] += 1
                        window_raw = pool[idx]
                        cached_probs = self.model_manager.get_unknown_device_probs(unk_dev)[idx]
                        use_fast_cache = True

            if use_fast_cache and cached_probs is not None:
                win_res = self.model_manager.score_probabilities(cached_probs, claimed, tau=self.tau)[0]
            else:
                window_raw = self._get_next_window_for_host(host_id)
                win_results = self.model_manager.score_windows(window_raw, claimed, tau=self.tau)
                win_res = win_results[0]

            self.window_history[host_id].append(win_res)

            # Keep rolling sparkline of IAT window means
            mean_iat = float(np.mean(window_raw))
            self.sparkline_history[host_id].append(round(mean_iat, 3))
            if len(self.sparkline_history[host_id]) > 20:
                self.sparkline_history[host_id].pop(0)

            # Compute device-level aggregate verdict (last 5 windows)
            dev_verdict_info = self.model_manager.compute_device_verdict(
                self.window_history[host_id],
                claimed_device=claimed,
                n_windows=self.agg_window_count,
                tau=self.tau
            )

            # Update State Machine
            sm = self.state_machines[host_id]
            sm_update = sm.update(
                device_level_verdict=dev_verdict_info["verdict"],
                confidence=dev_verdict_info["confidence"],
                predicted_device=dev_verdict_info.get("predicted_device") or ""
            )

            # Update host state representation
            hinfo["current_state"] = sm_update["current_state"]
            hinfo["window_verdict"] = win_res["verdict"]
            hinfo["device_verdict"] = dev_verdict_info["verdict"]
            hinfo["confidence"] = dev_verdict_info["confidence"]
            hinfo["predicted_device"] = dev_verdict_info.get("predicted_device")
            hinfo["probabilities"] = win_res["probabilities"]
            hinfo["firewall_action"] = sm_update["action"]
            hinfo["firewall_rules"] = sm_update["firewall_rules"]
            hinfo["sparkline"] = list(self.sparkline_history[host_id])

            self.scenario_metrics["total_windows_evaluated"] += 1

            # Check false alarm on legitimate hosts
            if not hinfo.get("is_attacker"):
                if self.active_scenario == "HIJACKED_DEVICE" and host_id == self.scenario_params.get("target_host"):
                    # After hijack tick, this host is technically compromised
                    pass
                else:
                    if sm_update["current_state"] in ["QUARANTINED", "ISOLATED"]:
                        self.scenario_metrics["false_alarms"] += 1

            # Check detection of attacker / hijacked host
            is_malicious = hinfo.get("is_attacker", False)
            if self.active_scenario == "HIJACKED_DEVICE" and host_id == self.scenario_params.get("target_host"):
                if self.tick_count >= self.scenario_params.get("hijack_at_tick", 6):
                    is_malicious = True

            if is_malicious and sm_update["current_state"] in ["QUARANTINED", "ISOLATED"]:
                self.scenario_metrics["detected"] = True
                if self.scenario_metrics["first_detection_tick"] is None:
                    self.scenario_metrics["first_detection_tick"] = self.tick_count

            # Create event if state transitioned or alert triggered
            if sm_update["transitioned"] or sm_update["alert"] or win_res["verdict"] != "VERIFIED":
                event = {
                    "tick": self.tick_count,
                    "timestamp": time.strftime("%H:%M:%S"),
                    "host_id": host_id,
                    "host_name": hinfo["name"],
                    "claimed_device": claimed,
                    "predicted_device": dev_verdict_info.get("predicted_device"),
                    "confidence": dev_verdict_info["confidence"],
                    "window_verdict": win_res["verdict"],
                    "device_verdict": dev_verdict_info["verdict"],
                    "state": sm_update["current_state"],
                    "action": sm_update["action"],
                    "alert": sm_update["alert"],
                    "rule_summary": sm_update["firewall_rules"]["summary"],
                    "iptables": sm_update["firewall_rules"]["iptables"],
                    "nftables": sm_update["firewall_rules"]["nftables"]
                }
                self.events.append(event)
                tick_events.append(event)

            host_updates[host_id] = copy.deepcopy(hinfo)

        return {
            "tick": self.tick_count,
            "scenario": self.active_scenario,
            "hosts": host_updates,
            "events": tick_events,
            "metrics": dict(self.scenario_metrics)
        }
