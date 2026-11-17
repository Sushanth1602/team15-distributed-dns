#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SERVER_COUNT="${1:-5}"

if [[ ! "$SERVER_COUNT" =~ ^(1|3|5)$ ]]; then
    echo "Usage: ./scripts/start_network.sh [1|3|5]"
    exit 1
fi

OSKEN_PYTHON="${OSKEN_PYTHON:-}"

if [[ -z "$OSKEN_PYTHON" && -n "${VIRTUAL_ENV:-}" ]]; then
    OSKEN_PYTHON="$VIRTUAL_ENV/bin/python"
fi

OSKEN_PYTHON="${OSKEN_PYTHON:-python3}"

if ! "$OSKEN_PYTHON" -c "import os_ken" 2>/dev/null; then
    echo "ERROR: OS-Ken not found using $OSKEN_PYTHON"
    echo "Set OSKEN_PYTHON to the Python executable containing OS-Ken."
    exit 1
fi

mkdir -p logs

echo "Starting OS-Ken controller..."

"$OSKEN_PYTHON" -c \
'from os_ken.base.app_manager import AppManager; AppManager.run_apps(["controller"])' \
> logs/controller.log 2>&1 &

CONTROLLER_PID=$!

cleanup() {
    echo "Stopping controller..."
    kill "$CONTROLLER_PID" 2>/dev/null || true
    wait "$CONTROLLER_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

sleep 3

if ! kill -0 "$CONTROLLER_PID" 2>/dev/null; then
    echo "ERROR: Controller failed to start."
    cat logs/controller.log
    exit 1
fi

echo "Starting Mininet with $SERVER_COUNT DNS servers..."

sudo python3 topology.py "$SERVER_COUNT"
