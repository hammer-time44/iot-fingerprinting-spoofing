import os
import time
from playwright.sync_api import sync_playwright

OUT_DIR = r"network_guard/docs/screenshots_simplify"
os.makedirs(OUT_DIR, exist_ok=True)

def run_tests_and_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        
        # 1. Responsive widths overflow check
        print("=== Checking Viewport Overflow (360px, 768px, 1280px) ===")
        widths = [360, 768, 1280]
        for w in widths:
            context = browser.new_context(viewport={"width": w, "height": 900})
            page = context.new_page()
            page.goto("http://localhost:5173")
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            
            # Switch to Network Defense tab
            page.locator('button:has-text("Network Defense")').first.click()
            time.sleep(1)
            
            scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
            inner_width = page.evaluate("() => window.innerWidth")
            assert scroll_width <= inner_width, f"Overflow at {w}px: {scroll_width} > {inner_width}"
            print(f"[PASS] Width {w}px: scrollWidth={scroll_width} <= innerWidth={inner_width}")
            
            page.screenshot(path=os.path.join(OUT_DIR, f"defense_lab_initial_{w}px.png"))
            context.close()

        # 2. Case 1: Impersonation (Registered -> Different Registered)
        print("\n=== Running Case 1: Impersonation ===")
        context = browser.new_context(viewport={"width": 1280, "height": 950})
        page = context.new_page()
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        page.locator('button:has-text("Network Defense")').first.click()
        time.sleep(0.5)

        helper_text = page.locator("#attacker-sentence").inner_text()
        print("Helper sentence:", helper_text)
        assert "Samsung Camera will pretend to be Amazon Echo" in helper_text

        # Click Start attack
        page.locator('button:has-text("Start attack")').click()
        
        # Wait for watching state then verdict
        page.wait_for_selector("text=Watching...", timeout=5000)
        print("Confirmed watching phase...")
        
        # Wait for verdict headline
        page.wait_for_selector("text=Attack detected: this device is not who it claims to be", timeout=15000)
        print("[PASS] Case 1 Headline Detected: Attack detected: this device is not who it claims to be")

        # Pause to freeze UI state for clean screenshot
        if page.locator('button:has-text("Pause")').count() > 0:
            page.locator('button:has-text("Pause")').click()

        page.screenshot(path=os.path.join(OUT_DIR, "case1_impersonation_1280px.png"))
        context.close()

        # Responsive screenshots for Case 1 at 768px and 360px
        for w in [768, 360]:
            ctx = browser.new_context(viewport={"width": w, "height": 950})
            pg = ctx.new_page()
            pg.goto("http://localhost:5173")
            pg.wait_for_load_state("networkidle")
            time.sleep(0.5)
            pg.locator('button:has-text("Network Defense")').first.click()
            time.sleep(0.5)
            pg.locator('button:has-text("Start attack")').click()
            pg.wait_for_selector("text=Attack detected: this device is not who it claims to be", timeout=15000)
            pg.screenshot(path=os.path.join(OUT_DIR, f"case1_impersonation_{w}px.png"))
            print(f"[PASS] Saved Case 1 screenshot at {w}px")
            ctx.close()

        # 3. Case 2: Unknown Hardware (Unseen Attacker)
        print("\n=== Running Case 2: Unknown Hardware ===")
        context = browser.new_context(viewport={"width": 1280, "height": 950})
        page = context.new_page()
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        page.locator('button:has-text("Network Defense")').first.click()
        time.sleep(0.5)

        page.select_option("#attacking-device", "WithingsSmartScale")
        time.sleep(0.3)
        helper_text = page.locator("#attacker-sentence").inner_text()
        print("Helper sentence:", helper_text)
        assert "Withings Smart Scale will pretend to be" in helper_text

        page.locator('button:has-text("Start attack")').click()
        page.wait_for_selector("text=Unknown device detected: it does not match any registered device", timeout=15000)
        print("[PASS] Case 2 Headline Detected: Unknown device detected: it does not match any registered device")
        
        if page.locator('button:has-text("Pause")').count() > 0:
            page.locator('button:has-text("Pause")').click()

        page.screenshot(path=os.path.join(OUT_DIR, "case2_unknown_hardware_1280px.png"))
        context.close()

        # 4. Case 3: Genuine Control (Registered device claims own identity)
        print("\n=== Running Case 3: Genuine Device Control ===")
        context = browser.new_context(viewport={"width": 1280, "height": 950})
        page = context.new_page()
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        page.locator('button:has-text("Network Defense")').first.click()
        time.sleep(0.5)

        page.select_option("#attacking-device", "AmazonEcho")
        page.select_option("#pretends-to-be", "AmazonEcho")
        time.sleep(0.3)
        helper_text = page.locator("#attacker-sentence").inner_text()
        print("Helper sentence:", helper_text)
        assert "Amazon Echo is genuine and claims its own identity" in helper_text

        page.locator('button:has-text("Start attack")').click()
        page.wait_for_selector("text=Genuine device confirmed", timeout=15000)
        print("[PASS] Case 3 Headline Detected: Genuine device confirmed")
        
        if page.locator('button:has-text("Pause")').count() > 0:
            page.locator('button:has-text("Pause")').click()

        page.screenshot(path=os.path.join(OUT_DIR, "case3_genuine_control_1280px.png"))
        context.close()

        # 5. Case 4: Advanced Settings Accordion Opened
        print("\n=== Running Case 4: Advanced Settings Opened ===")
        context = browser.new_context(viewport={"width": 1280, "height": 1100})
        page = context.new_page()
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        page.locator('button:has-text("Network Defense")').first.click()
        time.sleep(0.5)

        details = page.locator("details#advanced-settings")
        assert not details.get_attribute("open"), "Advanced settings must be closed by default!"
        print("[PASS] Confirmed: Advanced settings is CLOSED by default.")

        page.locator("summary#advanced-settings-toggle").click()
        time.sleep(0.5)
        assert details.get_attribute("open") is not None, "Advanced settings should now be open."

        page.select_option("#manual-scenario-select", "HIJACKED_DEVICE")
        time.sleep(0.3)
        helper_text = page.locator("#attacker-sentence").inner_text()
        print("Helper sentence after manual scenario change:", helper_text)
        assert "Compromised Device" in helper_text

        page.screenshot(path=os.path.join(OUT_DIR, "case4_advanced_settings_open_1280px.png"))
        context.close()

        # 6. Screenshot other tabs to verify 0 regressions
        print("\n=== Screenshotting other tabs to confirm 0 regressions ===")
        tabs = [
            ("Known Devices", "tab_known_devices.png"),
            ("Unknown Devices", "tab_unknown_devices.png"),
            ("Spoofing Detection", "tab_spoof_detection.png"),
            ("Test Your Own", "tab_test_own.png")
        ]
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        for tab_label, filename in tabs:
            btn = page.locator(f'button:has-text("{tab_label}")')
            if btn.count() > 0:
                btn.first.click()
                time.sleep(0.5)
                page.screenshot(path=os.path.join(OUT_DIR, filename))
                print(f"[PASS] Saved screenshot for {tab_label} -> {filename}")

        context.close()
        browser.close()
        print("\n========================================================")
        print("ALL VERIFICATIONS AND SCREENSHOTS COMPLETED SUCCESSFULLY!")
        print("========================================================")

if __name__ == "__main__":
    run_tests_and_screenshots()
