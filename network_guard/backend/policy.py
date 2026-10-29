"""
Response Policy Engine & Firewall Rule Generator (Pure Functions)
"""
from typing import Dict, Any


def decide_action(verdict: str) -> Dict[str, Any]:
    """
    Pure policy function mapping model/aggregate verdict to defense action.

    Mapping:
      VERIFIED          -> ALLOW
      SPOOF_SUSPECTED   -> QUARANTINE (+ alert)
      UNKNOWN_HARDWARE  -> ISOLATE (+ alert, isolate VLAN)
      INSUFFICIENT_DATA -> OBSERVE (allowed, limited rate, watching)
    """
    if verdict == "VERIFIED":
        return {
            "action": "ALLOW",
            "alert": False,
            "vlan": "home_iot",
            "target_state": "TRUSTED",
            "severity": "low",
            "description": "Timing profile verified against claimed device class. Full LAN access permitted.",
        }
    elif verdict == "SPOOF_SUSPECTED":
        return {
            "action": "QUARANTINE",
            "alert": True,
            "vlan": "quarantine_vlan",
            "target_state": "QUARANTINED",
            "severity": "critical",
            "description": "Timing fingerprint matches a different known device! MAC spoofing suspected. Trapped in remediation VLAN.",
        }
    elif verdict == "UNKNOWN_HARDWARE":
        return {
            "action": "ISOLATE",
            "alert": True,
            "vlan": "isolated_vlan",
            "target_state": "ISOLATED",
            "severity": "high",
            "description": "Confidence below threshold (foreign hardware). Device isolated from all local subnets.",
        }
    elif verdict == "INSUFFICIENT_DATA":
        return {
            "action": "OBSERVE",
            "alert": False,
            "vlan": "home_iot",
            "target_state": "OBSERVING",
            "severity": "info",
            "description": "Observing initial traffic windows (fewer than 5 observation windows). Monitored under standard rate limits.",
        }
    else:
        # Fallback safe policy
        return {
            "action": "OBSERVE",
            "alert": True,
            "vlan": "quarantine_vlan",
            "target_state": "OBSERVING",
            "severity": "warning",
            "description": f"Unknown verdict '{verdict}'. Safe observation mode active.",
        }


def generate_firewall_rules(host_ip: str, host_mac: str, action: str, vlan_id: int = 100) -> Dict[str, str]:
    """
    Generate syntactically correct, production-grade text firewall rules (nftables and iptables).
    NOTE: These rules are generated as TEXT only and are never executed against kernel interfaces.
    """
    clean_ip = host_ip.strip()
    clean_mac = host_mac.lower().strip()

    if action == "ALLOW":
        nft = (
            f"# [nftables: ALLOW] Host {clean_ip} ({clean_mac})\n"
            f"table inet filter {{\n"
            f"    chain forward {{\n"
            f"        ether saddr {clean_mac} ip saddr {clean_ip} accept comment \"Device Timing Verified: ALLOW\"\n"
            f"    }}\n"
            f"}}"
        )
        ipt = (
            f"# [iptables: ALLOW] Host {clean_ip} ({clean_mac})\n"
            f"iptables -A FORWARD -m mac --mac-source {clean_mac} -s {clean_ip} -j ACCEPT -m comment --comment \"Timing Verified: ALLOW\""
        )
    elif action == "QUARANTINE":
        nft = (
            f"# [nftables: QUARANTINE] Host {clean_ip} ({clean_mac}) - Redirect to Remediation Portal\n"
            f"table inet filter {{\n"
            f"    chain forward {{\n"
            f"        ether saddr {clean_mac} ip daddr 192.168.1.0/24 drop comment \"SPOOF SUSPECTED: Drop LAN traffic\"\n"
            f"        ether saddr {clean_mac} tcp dport {{80, 443}} redirect to :8443 comment \"Quarantine Captive Portal\"\n"
            f"    }}\n"
            f"}}"
        )
        ipt = (
            f"# [iptables: QUARANTINE] Host {clean_ip} ({clean_mac})\n"
            f"iptables -I FORWARD 1 -m mac --mac-source {clean_mac} -d 192.168.1.0/24 -j DROP -m comment --comment \"SPOOF SUSPECTED: Drop\"\n"
            f"iptables -t nat -A PREROUTING -m mac --mac-source {clean_mac} -p tcp -m multiport --dports 80,443 -j REDIRECT --to-ports 8443"
        )
    elif action == "ISOLATE":
        nft = (
            f"# [nftables: ISOLATE] Host {clean_ip} ({clean_mac}) - Complete Isolation\n"
            f"table inet filter {{\n"
            f"    chain forward {{\n"
            f"        ether saddr {clean_mac} drop comment \"UNKNOWN HARDWARE: Strict Isolation\"\n"
            f"    }}\n"
            f"    chain input {{\n"
            f"        ether saddr {clean_mac} drop comment \"UNKNOWN HARDWARE: Block Gateway Access\"\n"
            f"    }}\n"
            f"}}"
        )
        ipt = (
            f"# [iptables: ISOLATE] Host {clean_ip} ({clean_mac})\n"
            f"iptables -I FORWARD 1 -m mac --mac-source {clean_mac} -j DROP -m comment --comment \"UNKNOWN HARDWARE: Drop All\"\n"
            f"iptables -I INPUT 1 -m mac --mac-source {clean_mac} -j DROP -m comment --comment \"UNKNOWN HARDWARE: Drop Gateway\""
        )
    elif action == "OBSERVE":
        nft = (
            f"# [nftables: OBSERVE] Host {clean_ip} ({clean_mac}) - Observation Buffer\n"
            f"table inet filter {{\n"
            f"    chain forward {{\n"
            f"        ether saddr {clean_mac} ip saddr {clean_ip} limit rate 10/second accept comment \"OBSERVE: Rate-Limited\"\n"
            f"        ether saddr {clean_mac} ip saddr {clean_ip} drop comment \"OBSERVE: Excess Dropped\"\n"
            f"    }}\n"
            f"}}"
        )
        ipt = (
            f"# [iptables: OBSERVE] Host {clean_ip} ({clean_mac})\n"
            f"iptables -A FORWARD -m mac --mac-source {clean_mac} -s {clean_ip} -m limit --limit 10/s -j ACCEPT\n"
            f"iptables -A FORWARD -m mac --mac-source {clean_mac} -s {clean_ip} -j DROP -m comment --comment \"OBSERVE: Excess\""
        )
    else:
        nft = f"# [nftables: DEFAULT DROP]\ntable inet filter {{ chain forward {{ drop; }} }}"
        ipt = f"# [iptables: DEFAULT DROP]\niptables -A FORWARD -j DROP"

    return {
        "nftables": nft,
        "iptables": ipt,
        "action": action,
    }

