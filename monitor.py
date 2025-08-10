"""
Passive Network Monitor Module.

def _safe_setdefault(db, key, default):
    \"\"\"Compatibility helper: if db has setdefault, use it. If it's a Redis-backed store,
    call setdefault. If db is a plain dict, use dict.setdefault.
    \"\"\"
    try:
        if hasattr(db, 'setdefault'):
            return db.setdefault(key, default)
        elif hasattr(db, 'set'):
            # likely RedisDeviceStore
            val = db.get(key)
            if val is None:
                db.set(key, default)
                return default
            return val
    except Exception:
        pass
    # fallback to dict
    if isinstance(db, dict):
        return db.setdefault(key, default)
    return default


This module passively listens to network traffic to discover devices.
It is hardened with robust error handling to prevent crashes from malformed
packets and ensures a clean shutdown procedure.
"""

from scapy.all import sniff, ARP, DHCP
import threading
import logging
from metrics import METRICS_DEVICE_ADDITIONS
import time

class PassiveMonitor:
    """A class to passively monitor network traffic for device discovery."""

    def __init__(self, interface: str, device_db: dict, lock: threading.Lock):
        """
        interface: the network interface to sniff on (e.g., "eth0")
        device_db: a shared dictionary where devices will be stored (keyed by IP)
        lock: threading.Lock protecting device_db
        """
        self.interface = interface
        self.device_db = device_db
        self.lock = lock
        self.running = False
        self.logger = logging.getLogger('iseeyou.monitor')

    def _update_device(self, ip, mac=None, hostname=None, source="passive"):
        ts = int(time.time())
        # Determine if this is a new device (for metrics)
        try:
            prev = None
            try:
                prev = self.device_db.get(ip) if hasattr(self.device_db, 'get') else None
            except Exception:
                prev = None
        except Exception:
            prev = None

        with self.lock:
            entry = self.device_db.setdefault(ip, {})
            if mac:
                entry['mac'] = mac
            if hostname:
                entry['hostname'] = hostname
            entry['last_seen'] = ts
            entry['source'] = source
            # maintain a lightweight history count
            entry['seen_count'] = entry.get('seen_count', 0) + 1
            try:
                if prev is None:
                    METRICS_DEVICE_ADDITIONS.inc()
            except Exception:
                pass
        # Optionally emit events via external broadcaster if injected
        try:
            self.logger.debug("Updated device %s -> %s", ip, entry)
        except Exception:
            pass

    def _parse_dhcp_hostname(self, pkt):
        """Extract hostname from DHCP options if present."""
        try:
            if DHCP in pkt and hasattr(pkt, 'options'):
                for opt in pkt[DHCP].options:
                    # DHCP options are tuples like ('hostname', 'myhost') or ('end', None)
                    if isinstance(opt, tuple) and opt[0] == 'hostname':
                        return opt[1].decode() if isinstance(opt[1], bytes) else opt[1]
        except Exception:
            pass
        return None

    def _handle_packet(self, pkt):
        """A callback function to process each captured packet."""
        try:
            # ARP announcements / requests
            if ARP in pkt:
                try:
                    src_ip = pkt[ARP].psrc
                    src_mac = pkt[ARP].hwsrc
                    if src_ip and src_mac and src_ip != '0.0.0.0':
                        self._update_device(src_ip, mac=src_mac, source='arp')
                except Exception:
                    self.logger.exception("Error processing ARP packet")

            # DHCP / BOOTP client announcements (e.g., hostname)
            if DHCP in pkt:
                try:
                    bootp = pkt.getlayer('BOOTP')
                    ciaddr = getattr(bootp, 'ciaddr', None)
                    # DHCP discover/offer flows may use different fields; fall back to pkt[ARP] if present.
                    # Try to extract offered IP (yiaddr) or client IP
                    yiaddr = getattr(bootp, 'yiaddr', None)
                    ip = yiaddr or ciaddr or (pkt[ARP].psrc if ARP in pkt else None)
                    hostname = self._parse_dhcp_hostname(pkt)
                    mac = None
                    # Get client's hwaddr from BOOTP if possible
                    try:
                        hwd = getattr(bootp, 'chaddr', None)
                        if hwd:
                            # chaddr can be bytes; format as MAC
                            if isinstance(hwd, bytes):
                                mac = ':'.join(f"{b:02x}" for b in hwd[:6])
                            else:
                                mac = str(hwd)
                    except Exception:
                        mac = None

                    if ip:
                        self._update_device(ip, mac=mac, hostname=hostname, source='dhcp')
                except Exception:
                    self.logger.exception("Error processing DHCP packet")

        except Exception as e:
            # Prevent sniffer from dying on unexpected exceptions
            self.logger.exception("Unhandled exception in packet handler: %s", e)

    def _stop_filter(self, pkt):
        # scapy expects a callable that returns True to stop.
        return not self.running

    def _sniff(self):
        """Internal sniff loop that restarts on errors and respects shutdown flag."""
        while self.running:
            try:
                # Capture ARP and DHCP/BOOTP traffic commonly used to discover hosts
                sniff(filter="arp or (udp and (port 67 or port 68))",
                      prn=self._handle_packet,
                      store=False,
                      iface=self.interface,
                      stop_filter=self._stop_filter,
                      timeout=5)
            except Exception as e:
                self.logger.exception("Scapy sniffer encountered an error: %s. Restarting sniff loop.", e)
                time.sleep(2)

    def start(self) -> threading.Thread:
        """Starts the packet sniffing process in a background thread."""
        self.running = True
        thread = threading.Thread(target=self._sniff, name="PassiveMonitor", daemon=True)
        thread.start()
        return thread

    def stop(self):
        """Gracefully stops the packet sniffing thread."""
        self.logger.info("Stopping passive monitor...")
        self.running = False
