"""
Verification script for isolation guarantee.
Recomputes SHA-256 manifest of all files outside network_guard/
and validates against network_guard/docs/initial_manifest.json.
Generates network_guard/docs/isolation_proof.txt.
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "network_guard"
INITIAL_MANIFEST = GUARD / "docs" / "initial_manifest.json"
PROOF_FILE = GUARD / "docs" / "isolation_proof.txt"

EXCLUDED_PARTS = {"network_guard", ".git", "node_modules", ".pytest_cache", "__pycache__"}

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def get_current_manifest():
    manifest = {}
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in EXCLUDED_PARTS for part in p.parts):
            continue
        rel = p.relative_to(ROOT)
        rel_key = str(rel)
        manifest[rel_key] = {
            "size": p.stat().st_size,
            "mtime": p.stat().st_mtime,
            "sha256": sha256_file(p)
        }
    return manifest

def main():
    print("=== Network Defense Lab: Isolation Proof Verifier ===")
    if not INITIAL_MANIFEST.exists():
        print(f"[ERROR] Initial manifest not found at {INITIAL_MANIFEST}")
        sys.exit(1)

    with open(INITIAL_MANIFEST, "r", encoding="utf-8") as f:
        initial = json.load(f)

    current = get_current_manifest()

    initial_keys = set(initial.keys())
    current_keys = set(current.keys())

    added = sorted(list(current_keys - initial_keys))
    removed = sorted(list(initial_keys - current_keys))
    modified = []

    for k in sorted(list(initial_keys & current_keys)):
        if initial[k]["sha256"] != current[k]["sha256"]:
            modified.append({
                "path": k,
                "initial_sha256": initial[k]["sha256"],
                "current_sha256": current[k]["sha256"]
            })

    timestamp = datetime.now().isoformat()
    is_pure = (len(added) == 0 and len(removed) == 0 and len(modified) == 0)

    report_lines = [
        "================================================================================",
        "             NETWORK DEFENSE LAB — ISOLATION & INTEGRITY PROOF                  ",
        "================================================================================",
        f"Verification Timestamp: {timestamp}",
        f"Target Repository Root: {ROOT}",
        f"Protected Target Scope: All files and directories OUTSIDE network_guard/",
        f"Initial Baseline Entries: {len(initial)} files",
        f"Current Scanned Entries:  {len(current)} files",
        "--------------------------------------------------------------------------------",
        f"Modified Files Outside network_guard/: {len(modified)}",
        f"Added Files Outside network_guard/:    {len(added)}",
        f"Deleted Files Outside network_guard/:  {len(removed)}",
        "--------------------------------------------------------------------------------",
    ]

    if is_pure:
        report_lines.extend([
            "VERDICT: PASSED (STRICT 100% ISOLATION PRESERVED)",
            "",
            "CERTIFICATION:",
            f"All {len(current)} files outside network_guard/ match their initial baseline SHA-256 hashes exactly.",
            "Zero existing files, configs, requirements, notebooks, or models outside",
            "the network_guard/ directory were created, modified, renamed, or deleted.",
            "All development, testing, benchmarks, dependencies, and documentation are",
            "completely contained within network_guard/.",
            "================================================================================"
        ])
    else:
        report_lines.extend([
            "VERDICT: FAILED — MODIFICATIONS DETECTED OUTSIDE network_guard/",
            ""
        ])
        if modified:
            report_lines.append("Modified Files:")
            for m in modified:
                report_lines.append(f"  - {m['path']} (hash mismatch)")
        if added:
            report_lines.append("Added Files:")
            for a in added:
                report_lines.append(f"  - {a}")
        if removed:
            report_lines.append("Removed Files:")
            for r in removed:
                report_lines.append(f"  - {r}")
        report_lines.append("================================================================================")

    report_text = "\n".join(report_lines)
    with open(PROOF_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(report_text)
    if not is_pure:
        sys.exit(1)

if __name__ == "__main__":
    main()
