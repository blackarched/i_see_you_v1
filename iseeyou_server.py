#!/usr/bin/env python3
"""
iseeyou_server.py - production-ready bootstrapper for ISeeYou

Responsibilities:
- Read configuration (iseeyou.ini) and environment variables
- Configure logging (console + optional rotating file)
- Instantiate device DB and thread-safe lock
- Create and start PassiveMonitor, NetworkScanner, Scheduler
- Register monitor/scanner with the dashboard module (SSE, REST)
- Manage graceful shutdown on SIGINT/SIGTERM

Notes:
- This file expects the following project modules to exist and implement the described contract:
    monitor.PassiveMonitor(interface, device_db, lock, shutdown_event)
    scanner.NetworkScanner(config, device_db, lock, shutdown_event)
    scheduler.Scheduler(config, shutdown_event)
  and that PasssiveMonitor.start() returns a Thread, NetworkScanner.start(interval) returns list of Threads,
  and Scheduler.add_task(name, func, interval) schedules a periodic worker.
- Run scapy components with appropriate capabilities (CAP_NET_RAW) or as root.
"""

import os
import sys
import time
import signal
import logging
import logging.handlers
import threading
try:
    import redis as redislib
except Exception:
    redislib = None
from device_store import RedisDeviceStore, InMemoryDeviceStore
import configparser
from typing import Dict, Any

# Import project components
try:
    from monitor import PassiveMonitor
    from scanner import ActiveScanner
    from scheduler import Scheduler
    import dashboard
except Exception as e:
    # Import errors are fatal - report and exit
    print(f"Fatal import error: {e}", file=sys.stderr)
    raise

# -----------------------
# Configuration defaults
# -----------------------
DEFAULT_CONFIG_PATH = os.environ.get("ISEEYOU_CONFIG", "iseeyou/iseeyou.ini")
LOG_FILE = os.environ.get("ISEEYOU_LOGFILE", "/var/log/iseeyou/iseeyou.log")
LOG_LEVEL = os.environ.get("ISEEYOU_LOGLEVEL", "INFO").upper()

# Security: require a secret in production. For dev, fallback allowed but warn.
ISEEYOU_SECRET = os.environ.get("ISEEYOU_SECRET")
if not ISEEYOU_SECRET:
    logging.basicConfig(level=logging.INFO)
    logging.warning("Environment variable ISEEYOU_SECRET is not set. Using insecure defaults for development only.")
    ISEEYOU_SECRET = "dev-secret-iseeyou"  # must override in production

# -----------------------
# Helper functions
# -----------------------
def configure_logging(logfile: str = LOG_FILE, level: str = "INFO"):
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level))
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Rotating file handler - only add if path is writable
    try:
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(logfile, maxBytes=10*1024*1024, backupCount=5)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception as e:
        logging.warning("Could not create log file handler (%s). Continuing with console-only logging.", e)

# -----------------------
# Main server bootstrap
# -----------------------
def load_config(path: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    read = cfg.read(path)
    if not read:
        logging.warning("Configuration file '%s' not found or unreadable. Using defaults and environment variables.", path)
    return cfg

def require_root_or_capabilities():
    """Check for root or at least CAP_NET_RAW on Linux (best-effort)."""
    if os.name != "posix":
        return
    try:
        if os.geteuid() == 0:
            return
    except Exception:
        return
    # Not root. Warn: sniffing may fail without CAP_NET_RAW.
    logging.warning("Process not running as root. Passive monitor may require CAP_NET_RAW or root privileges to sniff packets. See README.")

def main():
    configure_logging(level=LOG_LEVEL)
    logging.info("Starting ISeeYou server bootstrap")

    config = load_config(DEFAULT_CONFIG_PATH)

    # Build device DB and lock
    device_db = None
    db_lock = None

    # Initialize device storage: prefer Redis if configured
    REDIS_URL = os.environ.get('REDIS_URL')
    redis_client = None
    if REDIS_URL and redislib is not None:
        try:
            redis_client = redislib.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
            redis_client.ping()
            device_db = RedisDeviceStore(redis_client)
            db_lock = None
            logging.info('Using Redis-backed device store')
        except Exception:
            logging.warning('Could not connect to Redis; falling back to in-memory store')
            device_db = InMemoryDeviceStore()
            db_lock = threading.RLock()
    else:
        device_db = InMemoryDeviceStore()
        db_lock = threading.RLock()


    # Global shutdown event for cooperative cancellation
    shutdown_event = threading.Event()

    require_root_or_capabilities()

    # Read network config (interface, scan interval) from config or env
    net_iface = os.environ.get("ISEEYOU_INTERFACE") or config.get("network", "interface", fallback="wlan0")
    scan_interval = int(os.environ.get("ISEEYOU_SCAN_INTERVAL") or config.get("network", "scan_interval", fallback="300"))

    # Instantiate components
    try:
        monitor = PassiveMonitor(interface=net_iface, device_db=device_db, lock=db_lock)
        logging.info("PassiveMonitor instantiated for interface: %s", net_iface)
    except Exception as e:
        logging.exception("Failed to instantiate PassiveMonitor: %s", e)
        raise

    try:
        # ActiveScanner needs subnet_cidr, device_db, lock, and optionally probe_ports
        subnet_cidr = os.environ.get("ISEEYOU_SUBNET") or config.get("network", "subnet", fallback="192.168.1.0/24")
        scanner = ActiveScanner(subnet_cidr=subnet_cidr, device_db=device_db, lock=db_lock)
        logging.info("ActiveScanner instantiated")
    except Exception as e:
        logging.exception("Failed to instantiate ActiveScanner: %s", e)
        raise

    try:
        scheduler = Scheduler()
        logging.info("Scheduler instantiated")
    except Exception as e:
        logging.exception("Failed to instantiate Scheduler: %s", e)
        raise

    # Register components with dashboard so REST and SSE can be used
    try:
        dashboard.register_monitor(monitor)
        dashboard.register_scanner(scanner)
        logging.info("Registered monitor and scanner with dashboard")
    except Exception as e:
        logging.exception("Failed to register components with dashboard: %s", e)
        raise

    # Create Flask app (attach shutdown_event so SSE can close on shutdown)
    app = dashboard.create_app(attach_shutdown_event=shutdown_event)

    # Start background components
    running_threads = {}

    # Start passive monitor (start returns a Thread or raises)
    try:
        t_mon = monitor.start()
        # Some implementations return thread object, others may return None; normalize
        if isinstance(t_mon, threading.Thread):
            running_threads["passive_monitor"] = t_mon
        logging.info("PassiveMonitor started (thread: %s)", getattr(t_mon, "name", str(t_mon)))
    except Exception as e:
        logging.exception("Failed to start PassiveMonitor: %s", e)
        # depending on policy, either exit or continue - choose to exit
        raise

    # Start scanner (start returns list of threads)
    try:
        worker_threads = scanner.start(interval=scan_interval)
        if isinstance(worker_threads, list):
            for t in worker_threads:
                if isinstance(t, threading.Thread):
                    running_threads[f"scanner_{t.name}"] = t
        logging.info("ActiveScanner started: %d threads", len(worker_threads) if worker_threads else 0)
    except Exception as e:
        logging.exception("Failed to start ActiveScanner: %s", e)
        raise

    # Example: schedule periodic active scan via scheduler using scanner.scan_once if available
    try:
        if hasattr(scanner, "scan_once"):
            scheduler.add_task("periodic_active_scan", lambda: safe_call(scanner.scan_once), interval=scan_interval)
            # Start scheduler (it should create its threads on add_task or have explicit start)
            # If Scheduler requires a start call, call scheduler.start() here.
            logging.info("Scheduled periodic active scans every %d seconds", scan_interval)
        else:
            logging.warning("Scanner does not expose scan_once; periodic scheduling skipped.")
    except Exception:
        logging.exception("Failed to register periodic scan task with Scheduler")

    # If scheduler needs to be started explicitly, start its threads here
    try:
        # Many Scheduler implementations start worker threads on add_task; call start if exists
        if hasattr(scheduler, "start"):
            s_threads = scheduler.start()
            if isinstance(s_threads, list):
                for t in s_threads:
                    if isinstance(t, threading.Thread):
                        running_threads[f"scheduler_{t.name}"] = t
            logging.info("Scheduler started")
    except Exception:
        # Not fatal if the scheduler doesn't need an explicit start
        logging.debug("Scheduler did not require explicit start or failed to start threads.")

    # Signal handlers to initiate clean shutdown
    def _signal_handler(signum, frame):
        logging.info("Received signal %s - initiating shutdown", signum)
        shutdown_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # If run directly, start dev Flask server; in production use gunicorn pointing at dashboard.create_app()
    try:
        # If this process is the main runner, run Flask in separate thread to allow same-process components.
        if __name__ == "__main__":
            # Start Flask dev server in non-blocking thread (dev only)
            def run_flask():
                logging.info("Starting Flask development server on 0.0.0.0:5000 (dev only)")
                app.run(host="0.0.0.0", port=5000, threaded=True)

            flask_thread = threading.Thread(target=run_flask, name="FlaskDevServer", daemon=True)
            flask_thread.start()
            running_threads["flask_dev"] = flask_thread

            # Main loop: wait until shutdown_event is set
            while not shutdown_event.is_set():
                time.sleep(1)
        else:
            # If run under gunicorn (WSGI), we don't run the Flask dev server; just block until shutdown
            while not shutdown_event.is_set():
                time.sleep(1)

    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received - shutting down")
        shutdown_event.set()
    finally:
        logging.info("Shutdown requested - stopping components...")

        # Stop scheduler tasks
        try:
            if hasattr(scheduler, "shutdown"):
                scheduler.shutdown()
        except Exception:
            logging.exception("Error shutting down scheduler")

        # Stop scanner
        try:
            if hasattr(scanner, "stop"):
                scanner.stop()
        except Exception:
            logging.exception("Error stopping scanner")

        # Stop passive monitor
        try:
            if hasattr(monitor, "stop"):
                monitor.stop()
        except Exception:
            logging.exception("Error stopping monitor")

        # Let dashboard do cleanup if any
        try:
            errs = dashboard.shutdown_components(timeout=5)
            if errs:
                logging.warning("Dashboard component shutdown reported issues: %s", errs)
        except Exception:
            logging.exception("Error calling dashboard.shutdown_components")

        # Wait for threads to join gracefully
        logging.info("Waiting for background threads to exit")
        for name, thread in list(running_threads.items()):
            try:
                if thread and thread.is_alive():
                    logging.info("Joining thread %s", name)
                    thread.join(timeout=5)
                    if thread.is_alive():
                        logging.warning("Thread %s did not exit cleanly", name)
            except Exception:
                logging.exception("Error joining thread %s", name)

        logging.info("ISeeYou service shutdown complete")

# Utility wrapper for scheduling: isolates exceptions
def safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logging.exception("Error in scheduled task: %s", e)
        return None

if __name__ == "__main__":
    main()
