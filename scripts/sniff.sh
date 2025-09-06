#!/bin/bash

# Network Sniffer Script

# Check if the necessary tools are installed
if ! command -v tshark &> /dev/null; then
    echo "tshark could not be found. Please install tshark and try again."
    exit 1
fi

# Function to capture network traffic
capture_traffic() {
    local interface=$1

    # Capture network traffic
    echo "Capturing network traffic on $interface..."
    sudo tshark -i $interface
}

# Main script
if [ $# -lt 1 ]; then
    echo "Usage: $0 <interface>"
    exit 1
fi

capture_traffic $1