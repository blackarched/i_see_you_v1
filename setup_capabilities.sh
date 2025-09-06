#!/bin/bash
# Setup script to grant necessary capabilities for ISeeYou
# This allows packet sniffing without running as root

set -e

echo "Setting up ISeeYou capabilities..."

# Find the Python executable in the virtual environment
PYTHON_PATH=$(readlink -f ../venv/bin/python3)

if [ ! -f "$PYTHON_PATH" ]; then
    echo "Error: Python executable not found at $PYTHON_PATH"
    echo "Make sure the virtual environment is set up correctly"
    exit 1
fi

echo "Found Python at: $PYTHON_PATH"

# Grant CAP_NET_RAW capability for packet sniffing
echo "Granting CAP_NET_RAW capability..."
sudo setcap cap_net_raw=eip "$PYTHON_PATH"

# Verify the capability was set
echo "Verifying capabilities..."
getcap "$PYTHON_PATH"

echo "Setup complete! You can now run ISeeYou without sudo for packet sniffing."
echo "To run: source ../venv/bin/activate && python3 iseeyou_server.py"
