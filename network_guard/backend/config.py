import os
import sys
import warnings
from pathlib import Path

# Suppress scikit-learn parallel execution user warnings in newer Python environments
warnings.filterwarnings("ignore", category=UserWarning)

# Paths
BACKEND_DIR = Path(__file__).resolve().parent
NETWORK_GUARD_DIR = BACKEND_DIR.parent
PROJECT_ROOT = NETWORK_GUARD_DIR.parent

# Add PROJECT_ROOT to sys.path so we can import src.features, src.spoof read-only
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Model & Data Artifact Paths (Existing Read-Only files)
DEFAULT_MODEL_PATH = PROJECT_ROOT / "results" / "step7_20261026_151020" / "rf_model.pkl"
DEFAULT_SCALER_PATH = PROJECT_ROOT / "results" / "raw_stat_scaler.pkl"
DATA_FEATURES_DIR = PROJECT_ROOT / "data" / "features"
RESULTS_DIR = NETWORK_GUARD_DIR / "results"
LOGS_DIR = NETWORK_GUARD_DIR / "logs"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Default Model Parameters
DEFAULT_TAU = 0.84
DEFAULT_WINDOW_SIZE = 128
DEFAULT_AGG_WINDOW_COUNT = 5  # n=5 windows for device-level verdict
DEFAULT_HYSTERESIS = 2        # 2 consecutive agreeing verdicts required to change state

# Network Port Defaults
BACKEND_PORT = int(os.environ.get("PORT", "8766"))
FRONTEND_PORT = int(os.environ.get("VITE_PORT", "5174"))

# Known Devices (in exact model class order)
KNOWN_DEVICES = [
    "AmazonEcho",
    "BelkinWemoMotionSensor",
    "PhilipsHue",
    "SamsungCamera",
    "TPLinkSmartPlug"
]

# Registered Home LAN Topology
REGISTERED_HOSTS = {
    "host-echo": {
        "id": "host-echo",
        "name": "Amazon Echo (Living Room)",
        "claimed_device": "AmazonEcho",
        "mac": "44:65:0D:56:CC:D3",
        "ip": "192.168.1.101",
        "network": "HOME_LAN",
        "icon": "Speaker"
    },
    "host-wemo": {
        "id": "host-wemo",
        "name": "Belkin WeMo Motion (Hallway)",
        "claimed_device": "BelkinWemoMotionSensor",
        "mac": "EC:1A:59:79:F4:89",
        "ip": "192.168.1.102",
        "network": "HOME_LAN",
        "icon": "Activity"
    },
    "host-hue": {
        "id": "host-hue",
        "name": "Philips Hue Bridge (Lighting Hub)",
        "claimed_device": "PhilipsHue",
        "mac": "00:17:88:24:76:FF",
        "ip": "192.168.1.103",
        "network": "HOME_LAN",
        "icon": "Lightbulb"
    },
    "host-cam": {
        "id": "host-cam",
        "name": "Samsung SmartCam (Entrance)",
        "claimed_device": "SamsungCamera",
        "mac": "00:16:6C:AB:6B:88",
        "ip": "192.168.1.104",
        "network": "HOME_LAN",
        "icon": "Camera"
    },
    "host-plug": {
        "id": "host-plug",
        "name": "TP-Link Smart Plug (Office)",
        "claimed_device": "TPLinkSmartPlug",
        "mac": "50:C7:BF:00:56:39",
        "ip": "192.168.1.105",
        "network": "HOME_LAN",
        "icon": "Power"
    }
}

GATEWAY_INFO = {
    "name": "Security Gateway & Timing Monitor",
    "mac": "52:54:00:12:34:56",
    "ip": "192.168.1.1",
    "lan_subnet": "192.168.1.0/24",
    "attacker_subnet": "10.0.0.0/24"
}
