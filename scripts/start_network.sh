#!/bin/bash
set -e

cd "$(dirname "$0")/.."

source ~/ryu39-env/bin/activate

echo "Starting OS-Ken SDN controller..."
osken-manager controller.py > logs/controller.log 2>&1 &
CONTROLLER_PID=$!

sleep 3

echo "Starting Mininet topology..."
sudo python3 topology.py

echo "Stopping controller..."
kill "$CONTROLLER_PID" 2>/dev/null || true
