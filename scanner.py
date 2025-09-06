"""
Active network scanner.

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


Performs on-demand or scheduled scanning of a subnet and probes hosts.
Implements a minimal, safe scanner that avoids aggressive behavior.
"""

import threading
import logging
import socket
import time
from concurrent.futures import ThreadPoolExecutor
import ipaddress
from metrics import METRICS_SCAN_DURATION, METRICS_SCAN_ERRORS, METRICS_DEVICE_ADDITIONS
from queue import Queue

class ActiveScanner:
    """
    Active scanner that probes hosts on a subnet.
    device_db is a shared dict (protected by lock externally) where scan results will be written.
    """

    def __init__(self, subnet_cidr: str, device_db: dict, lock, probe_ports=None, shutdown_event=None):
        self.subnet = ipaddress.ip_network(subnet_cidr, strict=False)
        self.device_db = device_db
        self.lock = lock
        self.shutdown_event = shutdown_event
        self.logger = logging.getLogger('iseeyou.scanner')
        self.running = threading.Event()
        self._threads = []
        self._vendor_q = Queue()
        # Common ports to probe for liveness; keep small to be polite.
        self.probe_ports = probe_ports or [80, 443, 22]
        self._last_scan = 0

    def _probe_tcp(self, ip, port, timeout=1.0):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                res = s.connect_ex((str(ip), port))
                return res == 0
        except Exception:
            return False

    def probe_host(self, ip):
        """Probe a single host for liveness and common open ports."""
        ip_str = str(ip)
        alive = False
        open_ports = []
        for p in self.probe_ports:
            if self._probe_tcp(ip_str, p, timeout=0.7):
                alive = True
                open_ports.append(p)
        if alive:
            # update device_db
            ts = int(time.time())
            try:
                with self.lock:
                    entry = self.device_db.setdefault(ip_str, {})
                    entry['last_seen'] = ts
                    entry['open_ports'] = open_ports
                    entry['source'] = 'active'
                    entry['seen_count'] = entry.get('seen_count', 0) + 1
                    try:
                        METRICS_DEVICE_ADDITIONS.inc()
                    except Exception:
                        pass
                    try:
                        METRICS_DEVICE_ADDITIONS.inc()
                    except Exception:
                        pass
            except Exception:
                self.logger.exception("Error updating device db for %s", ip_str)
        return alive

    def scan_once(self, target=None, max_workers=40):
        """Scan the given target (CIDR or single ip) or the scanner's subnet once."""
        self.logger.info("Starting on-demand active scan...")
        import time as _scan_time
        _scan_start = _scan_time.time()
        try:
            targets = []
            if target:
                # accept single ip or cidr
                try:
                    net = ipaddress.ip_network(target, strict=False)
                    targets = list(net.hosts())
                except Exception:
                    # maybe it's a single IP
                    targets = [ipaddress.ip_address(target)]
            else:
                targets = list(self.subnet.hosts())

            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                list(ex.map(self.probe_host, targets))
            self._last_scan = time.time()
            try:
                duration = _scan_time.time() - _scan_start
                METRICS_SCAN_DURATION.observe(duration)
            except Exception:
                pass
            self.logger.info("On-demand active scan complete.")
        except Exception as _scan_exc:
            try:
                METRICS_SCAN_ERRORS.inc()
            except Exception:
                pass
            self.logger.exception('Error during scan: %s', _scan_exc)
            raise
        return True

    def _vendor_lookup_worker(self):
        """Background worker that processes vendor lookup requests (non-blocking)."""
        while self.running.is_set():
            try:
                ip, mac = self._vendor_q.get(timeout=1)
                # Lightweight vendor resolution placeholder:
                vendor = None
                # If mac present, take OUI and map to vendor (not implemented here).
                if mac and len(mac) >= 8:
                    oui = mac.upper().replace(":", "")[0:6]
                    vendor = "unknown"  # production: query local OUI DB or external API
                # attach vendor info
                with self.lock:
                    if ip in self.device_db:
                        self.device_db[ip]['vendor'] = vendor
                self._vendor_q.task_done()
            except Exception:
                time.sleep(0.2)

    def trigger_scan(self, target=None):
        """Trigger a non-blocking scan in a new thread. Returns True if scan started."""
        if self.running.is_set():
            self.logger.info("Scan already in-progress; ignoring trigger.")
            return False
        self.running.set()
        t = threading.Thread(target=self._run_scan, args=(target,), daemon=True)
        t.start()
        return True

    def _run_scan(self, target):
        try:
            self.scan_once(target)
        finally:
            self.running.clear()

    def start(self, interval=300):
        """Start periodic scanning and the vendor worker; returns thread handles."""
        if self.running.is_set():
            self.logger.warning("Scanner already running")
            return self._threads
        self.logger.info("Starting network scanner with interval: %d seconds", interval)
        self.running.set()

        scan_thread = threading.Thread(target=self._periodic_scan_loop, args=(interval,), name="ScannerLoop", daemon=True)
        vendor_thread = threading.Thread(target=self._vendor_lookup_worker, name="VendorLookup", daemon=True)

        self._threads = [scan_thread, vendor_thread]
        for t in self._threads:
            t.start()
        return self._threads

    def _periodic_scan_loop(self, interval):
        while self.running.is_set():
            try:
                self.scan_once()
            except Exception:
                self.logger.exception("Error during periodic scan")
            # sleep but wake up early on stop
            for _ in range(int(interval)):
                if not self.running.is_set():
                    break
                time.sleep(1)

    def stop(self):
        """Stops the scanner and worker threads."""
        self.logger.info("Stopping active scanner...")
        self.running.clear()
        for t in self._threads:
            t.join(timeout=3.0)
        self.logger.info("Scanner stopped cleanly.")
