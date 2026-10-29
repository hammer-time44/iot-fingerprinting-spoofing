"""
Configuration & Constants for Network Defense Lab
"""
from pathlib import Path
import os

# Project Roots
GUARD_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = GUARD_ROOT.parent

# Configurable Ports (can be overridden by environment)
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", 8766))
FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", 5174))

# Default Confidence Threshold
DEFAULT_TAU = 0.84

# Authoritative Known Devices
KNOWN_DEVICES = [
    "AmazonEcho",
    "BelkinWemoMotionSensor",
    "PhilipsHue",
    "SamsungCamera",
    "TPLinkSmartPlug",
]

# Static Simulated Network Topology Configuration
HOME_NETWORK = {
    "subnet": "192.168.1.0/24",
    "gateway_ip": "192.168.1.1",
    "gateway_mac": "52:54:00:12:34:56",
}

ATTACKER_NETWORK = {
    "subnet": "10.0.99.0/24",
    "gateway_ip": "10.0.99.1",
}

# 5 Registered Home LAN Hosts
REGISTERED_HOSTS = {
    "host_echo": {
        "id": "host_echo",
        "name": "Amazon Echo Dot",
        "device_class": "AmazonEcho",
        "ip": "192.168.1.50",
        "mac": "44:65:0d:56:cc:d3",
        "vlan": "home_iot",
    },
    "host_wemo": {
        "id": "host_wemo",
        "name": "Belkin WeMo Motion",
        "device_class": "BelkinWemoMotionSensor",
        "ip": "192.168.1.51",
        "mac": "ec:1a:59:79:f4:89",
        "vlan": "home_iot",
    },
    "host_hue": {
        "id": "host_hue",
        "name": "Philips Hue Bridge",
        "device_class": "PhilipsHue",
        "ip": "192.168.1.52",
        "mac": "00:17:88:21:f7:ae",
        "vlan": "home_iot",
    },
    "host_cam": {
        "id": "host_cam",
        "name": "Samsung SmartCam",
        "device_class": "SamsungCamera",
        "ip": "192.168.1.53",
        "mac": "00:16:6c:ab:6b:88",
        "vlan": "home_iot",
    },
    "host_plug": {
        "id": "host_plug",
        "name": "TP-Link Smart Plug",
        "device_class": "TPLinkSmartPlug",
        "ip": "192.168.1.54",
        "mac": "50:c7:bf:00:56:39",
        "vlan": "home_iot",
    },
}

# Storage & Output Paths inside network_guard
RESULTS_DIR = GUARD_ROOT / "results"
LOGS_DIR = GUARD_ROOT / "logs"
DOCS_DIR = GUARD_ROOT / "docs"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

