#!/bin/bash

# WiFi Scanner Script

# Check if the necessary tools are installed
if ! command -v airodump-ng &> /dev/null; then
    echo "airodump-ng could not be found. Please install airodump-ng and try again."
    exit 1
fi

# Function to scan for WiFi networks
scan_wifi() {
    # Put the wireless interface in monitor mode
    echo "Putting wireless interface in monitor mode..."
    sudo airmon-ng start wlan0

    # Scan for WiFi networks
    echo "Scanning for WiFi networks..."
    sudo airodump-ng wlan0mon
}

# Main script
scan_wifi