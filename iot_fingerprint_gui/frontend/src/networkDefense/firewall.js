// Text-only firewall rule generator for Network Defense Lab
// Generates valid iptables and nftables configuration snippets as safe text.

export function generateFirewallRules({
  action,
  ip,
  mac,
  claimedDevice,
  targetDevice = '',
  confidence = 0.0,
  vlanId = 99
}) {
  const cleanMac = (mac || '').toLowerCase();
  const confStr = Number(confidence || 0).toFixed(2);

  if (action === 'ALLOW') {
    return {
      action: 'ALLOW',
      iptables: [
        `# [SIMULATION TEXT ONLY] Allow verified host ${claimedDevice}`,
        `iptables -A FORWARD -s ${ip} -m mac --mac-source ${cleanMac} -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT`,
        `iptables -A FORWARD -d ${ip} -m conntrack --ctstate ESTABLISHED -j ACCEPT`
      ].join('\n'),
      nftables: [
        `# [SIMULATION TEXT ONLY] Allow verified host ${claimedDevice}`,
        `nft add rule inet filter forward ip saddr ${ip} ether saddr ${cleanMac} ct state new,established accept comment "VERIFIED: ${claimedDevice}"`,
        `nft add rule inet filter forward ip daddr ${ip} ct state established accept`
      ].join('\n'),
      summary: `ALLOW: Unrestricted forward traffic permitted for ${claimedDevice} (${ip} / ${cleanMac}).`
    };
  }

  if (action === 'QUARANTINE') {
    return {
      action: 'QUARANTINE',
      iptables: [
        `# [SIMULATION TEXT ONLY] Quarantine suspected spoofing device claiming ${claimedDevice}`,
        `iptables -A FORWARD -s ${ip} -j DROP`,
        `iptables -t nat -A PREROUTING -s ${ip} -p tcp --dport 80 -j DNAT --to-destination 192.168.1.1:8443`,
        `iptables -A INPUT -s ${ip} -p tcp --dport 8443 -j ACCEPT # Captive Portal Warning`
      ].join('\n'),
      nftables: [
        `# [SIMULATION TEXT ONLY] Quarantine suspected spoofing device claiming ${claimedDevice}`,
        `nft add rule inet filter forward ip saddr ${ip} drop comment "SPOOF_SUSPECTED: Claimed=${claimedDevice}, Predicted=${targetDevice}"`,
        `nft add rule inet nat prerouting ip saddr ${ip} tcp dport 80 dnat to 192.168.1.1:8443`
      ].join('\n'),
      summary: `QUARANTINE: Traffic dropped from ${ip}; redirected to gateway security inspection portal.`
    };
  }

  if (action === 'ISOLATE') {
    return {
      action: 'ISOLATE',
      iptables: [
        `# [SIMULATION TEXT ONLY] Isolate unknown foreign hardware below tau threshold (${confStr})`,
        `iptables -A FORWARD -s ${ip} -j DROP`,
        `ip link add link eth0 name eth0.${vlanId} type vlan id ${vlanId} # Route to isolated VLAN ${vlanId}`,
        `ebtables -A FORWARD -s ${cleanMac} -j DROP`
      ].join('\n'),
      nftables: [
        `# [SIMULATION TEXT ONLY] Isolate unknown foreign hardware below tau threshold (${confStr})`,
        `nft add rule inet filter forward ip saddr ${ip} drop comment "ISOLATE: Unknown Hardware (conf=${confStr})"`,
        `nft add rule netdev filter ingress ether saddr ${cleanMac} set meta vlan id ${vlanId}`
      ].join('\n'),
      summary: `ISOLATE: Host ${ip} (${cleanMac}) relegated to containment VLAN ${vlanId}. WAN/LAN routing denied.`
    };
  }

  if (action === 'OBSERVE') {
    return {
      action: 'OBSERVE',
      iptables: [
        `# [SIMULATION TEXT ONLY] Rate-limited observation for ${claimedDevice} (< 5 windows)`,
        `iptables -A FORWARD -s ${ip} -m limit --limit 30/sec --limit-burst 50 -j ACCEPT`,
        `iptables -A FORWARD -s ${ip} -j LOG --log-prefix "[GATEWAY-OBSERVE] "`,
        `iptables -A FORWARD -s ${ip} -j DROP`
      ].join('\n'),
      nftables: [
        `# [SIMULATION TEXT ONLY] Rate-limited observation for ${claimedDevice} (< 5 windows)`,
        `nft add rule inet filter forward ip saddr ${ip} limit rate 30/second burst 50 packets accept comment "OBSERVE: ${claimedDevice}"`,
        `nft add rule inet filter forward ip saddr ${ip} log prefix "[GATEWAY-OBSERVE] "`,
        `nft add rule inet filter forward ip saddr ${ip} drop`
      ].join('\n'),
      summary: `OBSERVE: Accumulating timing moments for ${claimedDevice}. Low-bandwidth rate limit applied.`
    };
  }

  return {
    action: 'DEFAULT_DENY',
    iptables: `# [SIMULATION TEXT ONLY] Default Deny\niptables -A FORWARD -s ${ip} -j DROP`,
    nftables: `# [SIMULATION TEXT ONLY] Default Deny\nnft add rule inet filter forward ip saddr ${ip} drop`,
    summary: `DEFAULT_DENY: Traffic blocked for ${ip}.`
  };
}

