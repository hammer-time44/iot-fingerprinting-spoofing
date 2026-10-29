"""
Script to capture responsive screenshots with Playwright at 360px, 768px, and 1280px.
Verifies zero horizontal scroll overflow and saves PNGs to network_guard/docs/screenshots/.
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "network_guard"
SCREENSHOTS_DIR = GUARD / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

BACKEND_URL = "http://127.0.0.1:8766"
FRONTEND_URL = "http://localhost:5174"

def wait_for_url(url, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    print("=== Network Defense Lab Screenshot Capture ===")
    
    # 1. Start backend
    print(f"Starting Backend on {BACKEND_URL}...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "network_guard.backend.main:app", "--host", "127.0.0.1", "--port", "8766"],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # 2. Start frontend (vite preview)
    print(f"Starting Frontend on {FRONTEND_URL}...")
    frontend_proc = subprocess.Popen(
        ["cmd", "/c", "npm", "run", "preview", "--", "--port", "5174"],
        cwd=str(GUARD / "frontend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        if not wait_for_url(f"{BACKEND_URL}/health", timeout=15):
            raise RuntimeError("Backend failed to become healthy on port 8766")
        print("Backend is healthy!")

        if not wait_for_url(FRONTEND_URL, timeout=15):
            raise RuntimeError("Frontend failed to start on port 5174")
        print("Frontend is up!")

        viewports = [
            ("mobile", 360, 780),
            ("tablet", 768, 1024),
            ("desktop", 1280, 800)
        ]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            for name, width, height in viewports:
                print(f"\nCapturing viewports for {name} ({width}x{height})...")
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()

                page.goto(FRONTEND_URL)
                page.wait_for_timeout(2500)

                # Check horizontal overflow
                overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
                print(f"  [{name}] Tab 1 (Live Lab) - Horizontal overflow: {overflow}")
                
                # Tab 1: Live Lab
                page.screenshot(path=str(SCREENSHOTS_DIR / f"tab1_livelab_{name}_{width}px.png"), full_page=False)
                print(f"  Saved tab1_livelab_{name}_{width}px.png")

                # Switch to Tab 2: Scoreboard
                scoreboard_btn = page.locator("button:has-text('Scoreboard')")
                scoreboard_btn.click()
                page.wait_for_timeout(1000)
                overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
                print(f"  [{name}] Tab 2 (Scoreboard) - Horizontal overflow: {overflow}")
                page.screenshot(path=str(SCREENSHOTS_DIR / f"tab2_scoreboard_{name}_{width}px.png"), full_page=False)
                print(f"  Saved tab2_scoreboard_{name}_{width}px.png")

                # Switch to Tab 3: How It Works
                how_btn = page.locator("button:has-text('How It Works')")
                how_btn.click()
                page.wait_for_timeout(1000)
                overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
                print(f"  [{name}] Tab 3 (How It Works) - Horizontal overflow: {overflow}")
                page.screenshot(path=str(SCREENSHOTS_DIR / f"tab3_howitworks_{name}_{width}px.png"), full_page=False)
                print(f"  Saved tab3_howitworks_{name}_{width}px.png")

                context.close()

            browser.close()

        print("\nAll screenshots captured successfully in:", SCREENSHOTS_DIR)

    finally:
        print("Cleaning up background processes...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait(timeout=5)
        frontend_proc.wait(timeout=5)
        print("Cleanup complete.")

if __name__ == "__main__":
    main()
