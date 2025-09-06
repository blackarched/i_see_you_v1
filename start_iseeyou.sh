#!/bin/bash
# ISeeYou startup script with proper environment setup

set -e

echo "Starting ISeeYou Network Security Tool..."

# Change to the correct directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo "Error: Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source ../venv/bin/activate

# Check if capabilities are set up
echo "Checking capabilities..."
if getcap ../venv/bin/python3 | grep -q cap_net_raw; then
    echo "✓ CAP_NET_RAW capability found - packet sniffing enabled"
    RUN_MODE="normal"
else
    echo "⚠ No CAP_NET_RAW capability found - packet sniffing may not work"
    echo "To enable packet sniffing without sudo, run: ./setup_capabilities.sh"
    RUN_MODE="limited"
fi

# Set environment variables
export ISEEYOU_SECRET="$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")"
export ISEEYOU_ADMIN_PASS_HASH="$(python3 -c "import bcrypt; print(bcrypt.hashpw(b'iseeyou', bcrypt.gensalt()).decode())")"

echo "Environment configured"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Running as root - all features enabled"
    python3 iseeyou_server.py
else
    if [ "$RUN_MODE" = "normal" ]; then
        echo "Running with capabilities - all features enabled"
        python3 iseeyou_server.py
    else
        echo "Running without root - some features may be limited"
        echo "For full functionality, run with: sudo -E env 'PATH=$PATH' python3 iseeyou_server.py"
        python3 iseeyou_server.py
    fi
fi
