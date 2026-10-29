# Network Defense UI Simplification — Architectural Decisions

## 1. Goal & Two-Input Control Redesign
- **Decision:** The complex multi-slider scenario control panel is replaced by two primary, prominent dropdowns side by side on wide screens (stacked on mobile < 640px), followed by primary "Start attack" and secondary "Reset" action buttons:
  `[ Attacking device ▾ ]   [ Pretends to be ▾ ]   [ Start attack ]  [ Reset ]`
- **Device Name Formatting:** Raw CamelCase identifiers (e.g. `BelkinWemoMotionSensor`, `TPLinkSmartPlug`, `WithingsSmartScale`) are dynamically converted to human-friendly display titles (e.g. "Belkin WeMo Motion", "TP-Link Smart Plug", "Withings Smart Scale").
- **Dropdown Grouping:** The "Attacking device" dropdown groups items into:
  - `<optgroup label="Registered devices (5)">`: The 5 known devices from the trained model.
  - `<optgroup label="Unknown devices (N)">`: The 15 foreign unseen commercial IoT devices exported from the dataset.

## 2. Inferred Scenario Mapping Logic
- **Automatic Classification:** Users no longer select scenarios from an abstract technical dropdown:
  1. **Registered Attacker $\ne$ Claimed Identity:** Automatically maps to `IMPERSONATION` scenario (`source_device = attacker`, `claimed_device = claim`).
  2. **Unseen Attacker Device:** Automatically maps to `UNKNOWN_HARDWARE` scenario (`unseen_device = attacker`, `claimed_device = claim`).
  3. **Registered Attacker $==$ Claimed Identity:** Automatically maps to `GENUINE_CONTROL` (`source_device = claim`, `claimed_device = claim`) showing authentic verified transmission.
- **Sensible Defaults:** Default attacking device is `SamsungCamera` and claimed device is `AmazonEcho`. Clicking "Start attack" with zero configuration immediately executes an active impersonation demonstration.

## 3. Plain-Language Real-Time Result Card
- **Decision:** A high-visibility result card updates live as simulation ticks occur:
  - **Observation Phase ($< 5$ windows):** Displays `"Watching... (X of 5 windows)"`.
  - **Attack Detected:** Headline: `"Attack detected: this device is not who it claims to be"`. Subtext shows technical verdict `SPOOF_SUSPECTED`, action `QUARANTINE`, and real window count (`"Detected after N windows"`).
  - **Unknown Device:** Headline: `"Unknown device detected: it does not match any registered device"`. Subtext shows technical verdict `UNKNOWN_HARDWARE`, action `ISOLATE`, and real window count.
  - **Mimicry / Replay Evasion:** Headline: `"Not detected: the traffic looks like the claimed device"`. Subtext shows `VERIFIED`, action `ALLOW`, and the honest disclaimer: `"Timing alone can sometimes be imitated."`.
  - **Genuine Device Control:** Headline: `"Genuine device confirmed"`. Subtext shows `VERIFIED`, action `ALLOW`, and confirmation window count.

## 4. Preservation of Advanced Capabilities
- **Decision:** All original manual controls (scenario dropdown, quantile mimicry slider, speed selector, $\tau$ threshold slider) are placed in a clearly labeled `<details>` **"Advanced settings"** accordion that is **closed by default**.
- When closed, the two-input inferred mapping governs execution. If opened and a manual scenario is selected, the manual configuration takes precedence.

