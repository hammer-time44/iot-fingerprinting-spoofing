#!/usr/bin/env bash
# Network Defense Lab startup script for Linux / macOS

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "          Starting Network Defense Lab (Autonomous Gateway)           "
echo "======================================================================"

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 is required but not installed or not in PATH."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "[ERROR] npm is required but not installed or not in PATH."
    exit 1
fi

echo "[1/3] Launching FastAPI Backend on http://127.0.0.1:8766..."
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8766 --reload &
BACKEND_PID=$!

echo "[2/3] Launching Vite Frontend on http://localhost:5174..."
(cd "$SCRIPT_DIR/frontend" && npm run dev) &
FRONTEND_PID=$!

cleanup() {
    echo ""
    echo "Stopping Network Defense Lab..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup INT TERM

echo ""
echo "======================================================================"
echo "  Network Defense Lab is live!"
echo "  Backend:  http://127.0.0.1:8766"
echo "  Frontend: http://localhost:5174"
echo "  API Docs: http://127.0.0.1:8766/docs"
echo "  Press Ctrl+C to stop both servers."
echo "======================================================================"
echo ""

wait

