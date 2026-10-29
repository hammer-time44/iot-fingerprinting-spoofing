"""
Updates iot_fingerprint_gui/frontend/src/App.jsx purely additively:
1. Adds NetworkDefense import and Shield icon
2. Adds 'Network Defense' tab button
3. Adds 'NetworkDefense' render branch
"""

import sys
import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_JSX = ROOT / "iot_fingerprint_gui" / "frontend" / "src" / "App.jsx"
ORIG_APP_JSX = ROOT / "network_guard" / "backups" / "App.jsx.orig"
DIFF_FILE = ROOT / "network_guard" / "docs" / "app_jsx.diff"

DIFF_FILE.parent.mkdir(parents=True, exist_ok=True)

with open(ORIG_APP_JSX, "r", encoding="utf-8") as f:
    orig_lines = f.readlines()

new_lines = []
spoof_button_seen = False

for line in orig_lines:
    # 1. Imports
    if "from './components/SpoofCheck';" in line:
        new_lines.append(line)
        new_lines.append("import NetworkDefense from './NetworkDefense';\n")
    elif "from 'lucide-react';" in line and "ShieldAlert" in line and "Shield," not in line:
        new_lines.append(line.replace("ShieldAlert", "ShieldAlert, Shield"))
    # 2. Track spoof button
    elif "<span>Spoofing Detection</span>" in line:
        spoof_button_seen = True
        new_lines.append(line)
    elif "</button>" in line and spoof_button_seen:
        spoof_button_seen = False
        new_lines.append(line)
        new_lines.append("\n")
        new_lines.append("            <button\n")
        new_lines.append("              onClick={() => setActiveTab('defense')}\n")
        new_lines.append("              className={`flex items-center space-x-2 py-3.5 border-b-2 text-xs sm:text-sm font-semibold transition-colors whitespace-nowrap ${\n")
        new_lines.append("                activeTab === 'defense'\n")
        new_lines.append("                  ? 'border-indigo-600 dark:border-indigo-400 text-indigo-600 dark:text-indigo-400 font-bold'\n")
        new_lines.append("                  : 'border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-gray-200'\n")
        new_lines.append("              }`}\n")
        new_lines.append("            >\n")
        new_lines.append("              <Shield className=\"w-4 h-4\" />\n")
        new_lines.append("              <span>Network Defense</span>\n")
        new_lines.append("            </button>\n")
    # 3. Render branch
    elif "{activeTab === 'spoof' && <SpoofCheck globalThreshold={threshold} />}" in line:
        new_lines.append(line)
        new_lines.append("        {activeTab === 'defense' && <NetworkDefense globalThreshold={threshold} />}\n")
    else:
        new_lines.append(line)

with open(APP_JSX, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

# Generate unified diff
diff = list(difflib.unified_diff(
    orig_lines,
    new_lines,
    fromfile="App.jsx.orig",
    tofile="App.jsx",
    lineterm=""
))

diff_text = "\n".join(diff) + "\n"
with open(DIFF_FILE, "w", encoding="utf-8") as f:
    f.write(diff_text)

print("Unified diff generated:")
print(diff_text)
print(f"Saved diff to {DIFF_FILE}")
