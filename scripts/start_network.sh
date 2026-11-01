#!/bin/bash
set -e

cd "$(dirname "$0")/.."

SERVER_COUNT=${1:-5}

if [[ ! "$SERVER_COUNT" =~ ^(1|3|5)$ ]]; then
    echo "Usage: ./scripts/start_network.sh [1|3|5]"
    exit 1
fi

source ~/ryu39-env/bin/activate

mkdir -p logs

echo "Starting OS-Ken controller..."
osken-manager controller.py > logs/controller.log 2>&1 &
CONTROLLER_PID=$!

cleanup() {
    echo "Stopping controller..."
    kill "$CONTROLLER_PID" 2>/dev/null || true
}
trap cleanup EXIT

sleep 3

echo "Starting topology with $SERVER_COUNT DNS servers..."
sudo python3 topology.py "$SERVER_COUNT"
