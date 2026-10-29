"""
Firewall Rules Generator for Network Defense Lab.
Generates valid iptables and nftables syntax strings as TEXT ONLY.
Rules are NEVER applied to host networking interfaces.
"""

from typing import Dict, Any

def generate_firewall_rules(
    action: str,
    ip: str,
    mac: str,
    claimed_device: str,
    target_device: str = "",
    confidence: float = 0.0,
    vlan_id: int = 99
) -> Dict[str, str]:
    """
    Generate iptables and nftables configuration snippets corresponding to an action.

    Args:
        action: 'ALLOW', 'QUARANTINE', 'ISOLATE', 'OBSERVE'
        ip: Host IP address
        mac: Host MAC address
        claimed_device: Claimed device name
        target_device: Optional predicted target
        confidence: Confidence score
        vlan_id: Containment VLAN for isolation

    Returns:
        Dict with 'iptables', 'nftables', 'summary'
    """
    clean_mac = mac.lower()
    
    if action == "ALLOW":
        iptables = (
            f"# [SIMULATION TEXT ONLY] Allow verified host {claimed_device}\n"
            f"iptables -A FORWARD -s {ip} -m mac --mac-source {clean_mac} -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT\n"
            f"iptables -A FORWARD -d {ip} -m conntrack --ctstate ESTABLISHED -j ACCEPT"
        )
        nftables = (
            f"# [SIMULATION TEXT ONLY] Allow verified host {claimed_device}\n"
            f"nft add rule inet filter forward ip saddr {ip} ether saddr {clean_mac} ct state new,established accept comment \"VERIFIED: {claimed_device}\"\n"
            f"nft add rule inet filter forward ip daddr {ip} ct state established accept"
        )
        summary = f"ALLOW: Unrestricted forward traffic permitted for {claimed_device} ({ip} / {clean_mac})."

    elif action == "QUARANTINE":
        iptables = (
            f"# [SIMULATION TEXT ONLY] Quarantine suspected spoofing device claiming {claimed_device}\n"
            f"iptables -A FORWARD -s {ip} -j DROP\n"
            f"iptables -t nat -A PREROUTING -s {ip} -p tcp --dport 80 -j DNAT --to-destination 192.168.1.1:8443\n"
            f"iptables -A INPUT -s {ip} -p tcp --dport 8443 -j ACCEPT # Captive Portal Warning"
        )
        nftables = (
            f"# [SIMULATION TEXT ONLY] Quarantine suspected spoofing device claiming {claimed_device}\n"
            f"nft add rule inet filter forward ip saddr {ip} drop comment \"SPOOF_SUSPECTED: Claimed={claimed_device}, Predicted={target_device}\"\n"
            f"nft add rule inet nat prerouting ip saddr {ip} tcp dport 80 dnat to 192.168.1.1:8443"
        )
        summary = f"QUARANTINE: Traffic dropped from {ip}; redirected to gateway security inspection portal."

    elif action == "ISOLATE":
        iptables = (
            f"# [SIMULATION TEXT ONLY] Isolate unknown foreign hardware below tau threshold ({confidence:.2f})\n"
            f"iptables -A FORWARD -s {ip} -j DROP\n"
            f"ip link add link eth0 name eth0.{vlan_id} type vlan id {vlan_id} # Route to isolated VLAN {vlan_id}\n"
            f"ebtables -A FORWARD -s {clean_mac} -j DROP"
        )
        nftables = (
            f"# [SIMULATION TEXT ONLY] Isolate unknown foreign hardware below tau threshold ({confidence:.2f})\n"
            f"nft add rule inet filter forward ip saddr {ip} drop comment \"ISOLATE: Unknown Hardware (conf={confidence:.2f})\"\n"
            f"nft add rule netdev filter ingress ether saddr {clean_mac} set meta vlan id {vlan_id}"
        )
        summary = f"ISOLATE: Host {ip} ({clean_mac}) relegated to containment VLAN {vlan_id}. WAN/LAN routing denied."

    elif action == "OBSERVE":
        iptables = (
            f"# [SIMULATION TEXT ONLY] Rate-limited observation for {claimed_device} (< 5 windows)\n"
            f"iptables -A FORWARD -s {ip} -m limit --limit 30/sec --limit-burst 50 -j ACCEPT\n"
            f"iptables -A FORWARD -s {ip} -j LOG --log-prefix \"[GATEWAY-OBSERVE] \"\n"
            f"iptables -A FORWARD -s {ip} -j DROP"
        )
        nftables = (
            f"# [SIMULATION TEXT ONLY] Rate-limited observation for {claimed_device} (< 5 windows)\n"
            f"nft add rule inet filter forward ip saddr {ip} limit rate 30/second burst 50 packets accept comment \"OBSERVE: {claimed_device}\"\n"
            f"nft add rule inet filter forward ip saddr {ip} log prefix \"[GATEWAY-OBSERVE] \"\n"
            f"nft add rule inet filter forward ip saddr {ip} drop"
        )
        summary = f"OBSERVE: Accumulating timing moments for {claimed_device}. Low-bandwidth rate limit applied."

    else:
        iptables = f"# [SIMULATION TEXT ONLY] Default Deny\niptables -A FORWARD -s {ip} -j DROP"
        nftables = f"# [SIMULATION TEXT ONLY] Default Deny\nnft add rule inet filter forward ip saddr {ip} drop"
        summary = f"DEFAULT_DENY: Traffic blocked for {ip}."

    return {
        "action": action,
        "iptables": iptables,
        "nftables": nftables,
        "summary": summary
    }

