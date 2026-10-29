# Network Defense Lab — Dashboard Integration Decisions

## 1. Static-First Architecture
- **Decision:** The main dashboard is designed for static hosting on Vercel with no mandatory backend server. The "Network Defense" tab operates fully in client-side JavaScript, replaying precomputed probabilities and authentic IAT sparkline windows exported from the actual trained model and test splits.
- **Optional Backend:** If `import.meta.env.VITE_NETWORK_GUARD_API` is provided, the tab can seamlessly connect to the live FastAPI backend on port 8766; otherwise, it defaults to static replay mode with zero runtime dependencies.

## 2. Minimal File Footprint & Read-Only Existing Code
- **Decision:** In accordance with the prompt's hard rules, `App.jsx` in `iot_fingerprint_gui/frontend/src/` is modified purely additively (1 import, 1 tab button, 1 render branch).
- All integration logic is housed in:
  - `iot_fingerprint_gui/frontend/src/NetworkDefense.jsx`
  - Helper modules in `iot_fingerprint_gui/frontend/src/networkDefense/`
  - Precomputed data in `iot_fingerprint_gui/frontend/public/data/network_guard_data.json` (mirrored to `assets/evaluation/` and `dist/data/` following project conventions)
- Baseline backup saved to `network_guard/backups/App.jsx.orig`.
- Unified diff saved to `network_guard/docs/app_jsx.diff`.

## 3. Mathematical & Policy Parity
- **Decision:** The client-side simulation directly ports the exact mathematical formulations tested in `network_guard/backend/`:
  - Confidence calculation: $\max_c P(c)$
  - Threshold comparison against $\tau = 0.84$
  - Multi-window soft-voting aggregation over sliding $n=5$ window buffers
  - Hysteresis: requiring 2 consecutive matching device verdicts before transitioning between `OBSERVING`, `TRUSTED`, `QUARANTINED`, and `ISOLATED`
  - Text-only firewall rule generation producing exact `nftables` and `iptables` statements.
- Parity is certified against 200 randomized fixtures in `network_guard/tests/parity_fixtures.json`.

## 4. UI/UX Style Alignment
- **Decision:** Styled using Tailwind CSS classes and Lucide React icons already bundled in `iot_fingerprint_gui/frontend/package.json`.
- Uses plain SVG for the network topology graph and benchmark bar charts, maintaining zero new npm dependencies.
- Full responsive support for Mobile (360px), Tablet (768px), and Desktop (1280px), adhering to both Dark and Light mode themes.

