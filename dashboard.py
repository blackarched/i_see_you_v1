"""
dashboard.py — Production-ready Flask dashboard binding for ISeeYou project.

Features:
- WSGI-ready Flask app factory (works with gunicorn)
- Secure login that issues HTTP-only secure cookie (HMAC token; switch to JWT/IDM as needed)
- Session verification decorator (cookie-based)
- SSE /events endpoint for real-time device push (simple in-process pubsub)
- REST endpoints: /api/devices, /api/scan (trigger), /health, /login, /logout
- After-request security headers (CSP, HSTS, X-Frame-Options, etc.)
- Graceful shutdown helper integration (expects an externally-provided shutdown_event)
- Simple device registry wiring helpers so external Monitor/Scanner can push updates
- Guidance: attach your PassiveMonitor and ActiveScanner instances using `register_monitor(...)` and `register_scanner(...)`

Notes:
- This module intentionally uses a simple in-process pubsub (Queue per subscriber). For multi-process scaling, replace with Redis Pub/Sub or similar.
- Must run behind HTTPS in production (nginx/traefik + certbot). Set ISEEYOU_FORCE_SECURE_COOKIE=1 in prod.
"""

import os
import time
import hmac
import hashlib
import json
import logging
import threading
import queue
from typing import Any, Dict, List, Callable, Optional
from functools import wraps
import bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
try:
    from flask_seasurf import SeaSurf
except Exception:
    SeaSurf = None
try:
    from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
except Exception:
    Counter = Gauge = generate_latest = CONTENT_TYPE_LATEST = None
try:
    from flask_talisman import Talisman
except Exception:
    Talisman = None

# Optional Redis for session revocation/persistence
try:
    import redis as redislib
except Exception:
    redislib = None


from flask import (
    Flask,
    request,
    jsonify,
    make_response,
    Response,
    stream_with_context,
    current_app,
)

# Optional dependency - enables strict security header management
try:
    from talisman import Talisman  # type: ignore
    _HAS_TALISMAN = True
except Exception:
    _HAS_TALISMAN = False
_DEVICE_DB = None


# --- Configuration defaults (override with env vars) ---
SECRET = os.environ.get('ISEEYOU_SECRET')
if not SECRET:
    # Allow fallback in dev but log stern warning
    SECRET = "dev-iseeyou-secret"  # ensure to override in production
    logging.warning("ISEEYOU_SECRET not set. Using insecure default. Set env var in production!")

SESSION_EXP_SECONDS = int(os.environ.get("ISEEYOU_SESSION_EXP", "3600"))

# Environment mode: 'production' enables strict checks.
ENV = os.environ.get("ENV", os.environ.get("ISEEYOU_ENV", "dev")).lower()

# Enforce presence of secret in production
if not SECRET:
    if ENV == "production" or os.environ.get("REQUIRE_SECRET", "1") == "1":
        raise RuntimeError("ISEEYOU_SECRET must be set in production. Set the ISEEYOU_SECRET environment variable.")
    SECRET = "dev-iseeyou-secret"
    logging.warning("ISEEYOU_SECRET not set. Using insecure default for development only. Set env var in production!")

# Admin credentials: prefer hashed password
ADMIN_USER = os.environ.get("ISEEYOU_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ISEEYOU_ADMIN_PASS")  # plain password (dev only)
ADMIN_PASS_HASH = os.environ.get("ISEEYOU_ADMIN_PASS_HASH")  # bcrypt hash recommended

# In production require at least one of ADMIN_PASS or ADMIN_PASS_HASH and avoid default 'changeme'
if ENV == "production":
    if not ADMIN_PASS_HASH and not ADMIN_PASS:
        raise RuntimeError("In production you must set ISEEYOU_ADMIN_PASS_HASH or ISEEYOU_ADMIN_PASS environment variable.")
    if ADMIN_PASS == "changeme":
        raise RuntimeError("ISEEYOU_ADMIN_PASS must be changed from default 'changeme' in production.")



# Optional Redis client for session revocation and simple persistence.
REDIS_URL = os.environ.get("REDIS_URL")
_redis_client = None
if REDIS_URL and redislib is not None:
    try:
        _redis_client = redislib.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        # test connection
        _redis_client.ping()
        logging.info("Connected to Redis for session/persistence: %s", REDIS_URL)
    except Exception as e:
        logging.warning("Could not connect to REDIS_URL (%s): %s. Continuing without redis.", REDIS_URL, e)
else:
    if REDIS_URL:
        logging.warning("REDIS_URL provided but redis library not available. Install 'redis' package.")
FORCE_SECURE_COOKIE = os.environ.get("ISEEYOU_FORCE_SECURE_COOKIE", "1") in ("1", "true", "True")
SSE_QUEUE_MAXSIZE = int(os.environ.get("ISEEYOU_SSE_QUEUE_MAX", "100"))

# --- Prometheus metrics (optional) ---
# These will be no-ops if prometheus_client is not installed.
if Counter is not None:
    METRICS_LOGIN_ATTEMPTS = Counter('iseeyou_login_attempts_total', 'Total login attempts')
    METRICS_LOGIN_FAILURES = Counter('iseeyou_login_failures_total', 'Login failures')
    METRICS_SCAN_REQUESTS = Counter('iseeyou_scan_requests_total', 'Active scan triggers')
    METRICS_DEVICES = Gauge('iseeyou_devices_count', 'Number of tracked devices')
else:
    METRICS_LOGIN_ATTEMPTS = METRICS_LOGIN_FAILURES = METRICS_SCAN_REQUESTS = METRICS_DEVICES = None


# App global registries (thread-safe primitives provided)
_device_db_lock = threading.RLock()
_device_db: Dict[str, Dict[str, Any]] = {}  # keyed by MAC or device-id


# --- Device store helpers (works with dict-like or custom store implementations) ---
def _store_get(key):
    try:
        if hasattr(_device_db, 'get'):
            return _device_db.get(key)
    except Exception:
        pass
    try:
        # dict fallback
        with _device_db_lock:
            return _device_db.get(key) if isinstance(_device_db, dict) else None
    except Exception:
        return None

def _store_set(key, value):
    try:
        if hasattr(_device_db, 'set'):
            return _device_db.set(key, value)
    except Exception:
        pass
    # dict fallback
    with _device_db_lock:
        _device_db[key] = value

def _store_setdefault(key, default):
    try:
        if hasattr(_device_db, 'setdefault'):
            return _device_db.setdefault(key, default)
        if hasattr(_device_db, 'set'):
            return _device_db.setdefault(key, default)
    except Exception:
        pass
    with _device_db_lock:
        return _device_db.setdefault(key, default)

def _store_items():
    try:
        if hasattr(_device_db, 'items'):
            return list(_device_db.items())
        if hasattr(_device_db, 'keys'):
            return [(k, _device_db.get(k)) for k in _device_db.keys()]
    except Exception:
        pass
    with _device_db_lock:
        return list(_device_db.items()) if isinstance(_device_db, dict) else []

# --- Monitor/Scanner registration helpers ---
def register_monitor(monitor):
    global _MONITOR
    _MONITOR = monitor
    return True

def register_scanner(scanner):
    global _SCANNER
    _SCANNER = scanner
    return True

# SSE subscriptions (list of queue.Queue) — small in-process pubsub
_sse_subs_lock = threading.RLock()
_sse_subs: List[queue.Queue] = []

# References to monitor/scanner components if attached
_MONITOR = None
_SCANNER = None

# Shutdown Event hook (to be set by the server bootstrap)
shutdown_event: Optional[threading.Event] = None

# --- Utilities ---

def _now_ts() -> int:
    return int(time.time())

def issue_session_token(user_id: str, expires_seconds: int = SESSION_EXP_SECONDS) -> str:
    """Issue a simple HMAC-bound session token: "user:exp:hexsig"
    Replace with JWT or OSS IDM for production.
    If Redis is configured, store the token in Redis so it can be revoked server-side.
    """
    exp = _now_ts() + expires_seconds
    payload = f"{user_id}:{exp}"
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token = f"{payload}:{sig}"
    # Store in Redis for server-side revocation if available
    try:
        if _redis_client:
            key = f"iseeyou:session:{token}"
            _redis_client.set(key, user_id, ex=expires_seconds)
    except Exception:
        logging.exception("Error storing session token in Redis")
    return token

def verify_session_token(token: str) -> Optional[str]:
    try:
        user, exp_s, sig = token.rsplit(":", 2)
        expected = hmac.new(SECRET.encode(), f"{user}:{exp_s}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        if int(exp_s) < _now_ts():
            return None
        # If Redis is enabled, ensure token is present (not revoked)
        try:
            if _redis_client:
                key = f"iseeyou:session:{token}"
                if not _redis_client.exists(key):
                    return None
        except Exception:
            logging.exception("Error checking session token in Redis")
            # fail safe: assume token invalid if redis check errors? We'll allow token if redis check fails.
        return user
    except Exception:
        return None

def require_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.cookies.get("iseeyou_session")
        if not token:
            return jsonify({"error": "unauthenticated"}), 401
        user = verify_session_token(token)
        if not user:
            return jsonify({"error": "invalid or expired session"}), 401
        # attach user to request context if needed
        request._iseeyou_user = user
        return func(*args, **kwargs)
    return wrapper

def broadcast_device_event(device: Dict[str, Any]) -> None:
    """
    Push device event to all active SSE subscribers (non-blocking).
    Device should be JSON-serializable.
    """
    with _sse_subs_lock:
        for q in list(_sse_subs):
            try:
                q.put_nowait(device)
            except queue.Full:
                # subscriber lagging — drop event for that subscriber
                continue

def update_device_db(device: Dict[str, Any]) -> None:
    """
    Update the device DB using store helpers. Device must contain 'mac'.
    """
    mac = device.get("mac")
    if not mac:
        return
    try:
        existing = _store_get(mac) or {}
    except Exception:
        existing = {}
    existing.update(device)
    existing["last_seen"] = _now_ts()
    try:
        _store_set(mac, existing)
    except Exception:
        # fallback to dict
        try:
            with _device_db_lock:
                _device_db[mac] = existing
        except Exception:
            pass
    # broadcast to SSE
    broadcast_device_event({"type": "device_update", "device": existing})

# --- Flask app factory ---


def create_app(*, attach_shutdown_event: Optional[threading.Event] = None) -> Flask:
    """
    Create and configure the Flask application for the dashboard.
    This factory returns a fully configured Flask app.
    """
    global shutdown_event, _sse_subs, _sse_subs_lock
    shutdown_event = attach_shutdown_event

    app = Flask(__name__, static_folder="static", template_folder="templates")

    # --- CSRF protection (Flask-SeaSurf) ---
    if SeaSurf is not None:
        try:
            csrf = SeaSurf(app)
            app.logger.info("Flask-SeaSurf CSRF protection enabled")
        except Exception:
            app.logger.exception("Failed to initialize Flask-SeaSurf")

    # --- Force HTTPS / Security headers (Talisman) ---
    if ENV == "production":
        app.config.update({
            "PREFERRED_URL_SCHEME": "https",
            "SESSION_COOKIE_SECURE": True,
            "REMEMBER_COOKIE_SECURE": True,
        })
        if Talisman is not None:
            try:
                Talisman(app, force_https=True)
                app.logger.info("Talisman enabled (security headers + HTTPS enforcement)")
            except Exception:
                app.logger.exception("Failed to initialize Talisman")
        else:
            app.logger.warning("Flask-Talisman not installed; ensure TLS is enforced at proxy level")

    # --- Prometheus metrics endpoint ---
    if generate_latest is not None:
        @app.route('/metrics')
        def metrics_endpoint():
            try:
                # update dynamic gauge of devices
                try:
                    # compute device count
                    count = 0
                    if _SCANNER is None and _MONITOR is None:
                        pass
                    # try device db if available
                    try:
                        if hasattr(_DEVICE_DB, 'keys'):
                            # if RedisDeviceStore, keys() returns list
                            count = len(_DEVICE_DB.keys())
                        else:
                            # if dict-like
                            count = len(_DEVICE_DB)
                    except Exception:
                        count = 0
                    if METRICS_DEVICES is not None:
                        try:
                            METRICS_DEVICES.set(count)
                        except Exception:
                            pass
                except Exception:
                    pass
                data = generate_latest()
                return Response(data, mimetype=CONTENT_TYPE_LATEST)
            except Exception:
                return Response('error', status=500)


    # Rate limiter (protect login endpoint)
    limiter = Limiter(key_func=get_remote_address)
    limiter.init_app(app)

    # Optional: use Flask-Talisman if installed for easier CSP/HSTS setup
    if _HAS_TALISMAN:
        csp = {
            "default-src": ["'self'"],
            "script-src": ["'self'"],
            "style-src": ["'self'"],
        }
        Talisman(app, content_security_policy=csp, force_https=FORCE_SECURE_COOKIE)

    # Security headers (safe fallback if Talisman not present)
    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=()")
        if FORCE_SECURE_COOKIE:
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        return response

    @app.route("/health", methods=["GET"])
    def health():
        """
        Health check that returns component statuses.
        Useful for load balancers and systemd.
        """
        monitor_status = "attached" if _MONITOR is not None else "missing"
        scanner_status = "attached" if _SCANNER is not None else "missing"
        return jsonify({
            "ok": True,
            "monitor": monitor_status,
            "scanner": scanner_status,
            "shutdown_requested": bool(shutdown_event and shutdown_event.is_set()),
            "time": _now_ts()
        })

    @app.route("/login", methods=["POST"])
    @limiter.limit("5 per minute")
    def login():
        if METRICS_LOGIN_ATTEMPTS is not None:
            try:
                METRICS_LOGIN_ATTEMPTS.inc()
            except Exception:
                pass

        """
        Simple username/password endpoint.
        Replace password check with secure userstore (hashed passwords / pluggable IAM).
        Accepts JSON: { "username": "...", "password": "..." }
        Issues HTTP-only secure cookie.
        """
        try:
            data = request.get_json(force=True)
        except Exception:
            return jsonify({"error": "invalid json"}), 400

        username = (data or {}).get("username")
        password = (data or {}).get("password")
        if not username or not password:
            return jsonify({"error": "username and password required"}), 400

        # Credentials verification using either bcrypt hash (recommended) or plaintext env (dev)
        if ADMIN_PASS_HASH:
            try:
                if not bcrypt.checkpw(password.encode(), ADMIN_PASS_HASH.encode()):
                    if METRICS_LOGIN_FAILURES is not None:
                        try:
                            METRICS_LOGIN_FAILURES.inc()
                        except Exception:
                            pass
                    return jsonify({"error": "invalid credentials"}), 401
            except Exception:
                logging.exception("Error verifying hashed admin password")
                if METRICS_LOGIN_FAILURES is not None:
                    try:
                        METRICS_LOGIN_FAILURES.inc()
                    except Exception:
                        pass
                return jsonify({"error": "invalid credentials"}), 401
        else:
            # Fallback to plaintext admin pass (DEV ONLY)
            if username != ADMIN_USER or password != (ADMIN_PASS or ""):
                if METRICS_LOGIN_FAILURES is not None:
                    try:
                        METRICS_LOGIN_FAILURES.inc()
                    except Exception:
                        pass
                return jsonify({"error": "invalid credentials"}), 401

        token = issue_session_token(username)
        resp = make_response(jsonify({"message": "ok"}))
        secure_flag = FORCE_SECURE_COOKIE
        # In dev, if you are testing on http://localhost, you may need to set FORCE_SECURE_COOKIE=0
        resp.set_cookie("iseeyou_session", token, httponly=True, secure=secure_flag, samesite="Lax")
        return resp

    @app.route("/logout", methods=["POST"])
    @require_session
    def logout():
        resp = make_response(jsonify({"message": "logged out"}))
        # Remove server-side session record if present
        try:
            token = request.cookies.get("iseeyou_session")
            if token and _redis_client:
                key = f"iseeyou:session:{token}"
                _redis_client.delete(key)
        except Exception:
            logging.exception("Error deleting session token from Redis")
        resp.delete_cookie("iseeyou_session")
        return resp

    @app.route("/api/devices", methods=["GET"])
    @require_session
    def api_devices():
        """
        Return all known devices. This is intentionally synchronous and returns a snapshot.
        For large scale, implement pagination and backend DB.
        """
        devices = []
        try:
            items = _store_items()
            devices = [v for (_, v) in items]
        except Exception:
            # fallback: try dict copy
            try:
                with _device_db_lock:
                    devices = list(_device_db.values())
            except Exception:
                devices = []
        return jsonify({"devices": devices, "count": len(devices)})

    @app.route("/api/devices/<mac>", methods=["GET"])
    @require_session
    def api_device(mac):
        device = _store_get(mac.lower())
        if not device:
            return jsonify({"error": "device not found"}), 404
        return jsonify({"device": device})

    @app.route("/api/scan", methods=["POST"])
    @require_session
    def api_scan():
        """
        Trigger an active scan via attached scanner component.
        Requires that the project provides an ActiveScanner with a .trigger_scan(subnet|ip) method.
        """
        if _SCANNER is None:
            return jsonify({"error": "scanner not attached"}), 503
        payload = request.get_json(silent=True) or {}
        target = payload.get("target")  # e.g., "192.168.1.0/24" or "192.168.1.10"
        try:
            started = _SCANNER.trigger_scan(target)
            if METRICS_SCAN_REQUESTS is not None:
                try:
                    METRICS_SCAN_REQUESTS.inc()
                except Exception:
                    pass
            return jsonify({"started": bool(started)})
        except Exception as e:
            logging.exception("Error triggering scan")
            return jsonify({"error": str(e)}), 500

    @app.route("/events")
    @require_session
    def sse_events():
        """
        Server-Sent Events endpoint for real-time device updates.
        Keep-alive is automatic from the client EventSource.
        """
        q = queue.Queue(maxsize=SSE_QUEUE_MAXSIZE)
        with _sse_subs_lock:
            _sse_subs.append(q)

        def gen():
            try:
                # initial handshake: send current devices snapshot
                try:
                    items = _store_items()
                    snapshot = [v for (_, v) in items]
                except Exception:
                    snapshot = []
                yield "event: snapshot\\n"
                yield f"data: {json.dumps(snapshot)}\\n\\n"
                while True:
                    try:
                        device = q.get(timeout=30)
                        yield "event: device_update\\n"
                        yield f"data: {json.dumps(device)}\\n\\n"
                    except queue.Empty:
                        # keep-alive
                        yield ": keepalive\\n\\n"
            finally:
                with _sse_subs_lock:
                    try:
                        _sse_subs.remove(q)
                    except ValueError:
                        pass

        return Response(stream_with_context(gen()), mimetype="text/event-stream")

    # Allow cross-origin for local dev if needed — remove in prod or scope to your frontend host.
    @app.after_request
    def maybe_allow_cors(response):
        if os.environ.get("ISEEYOU_ALLOW_CORS", "0") == "1":
            response.headers.setdefault("Access-Control-Allow-Origin", "*")
            response.headers.setdefault("Access-Control-Allow-Credentials", "true")
        return response

    return app


# === Auto-wired new dashboard integration ===
# Commented out due to undefined 'bp' variable
# from flask import send_from_directory
# import os, json

# @bp.route('/dashboard')
# def serve_dashboard():
#     dist_dir = os.path.join(os.path.dirname(__file__), 'frontend_dist')
#     index_file = os.path.join(dist_dir, 'index.html')
#     if os.path.exists(index_file):
#         return send_from_directory(dist_dir, 'index.html')
#     return "<h1>Dashboard build not found</h1>"

# @bp.route('/api/entities/<entity_name>')
# def get_entity_data(entity_name):
#     src_dir = os.path.join(os.path.dirname(__file__), 'frontend_src', 'entities')
#     json_path = os.path.join(src_dir, f"{entity_name}.json")
#     if os.path.exists(json_path):
#         return json.load(open(json_path))
#     return {}, 404

# @bp.route('/api/scan', methods=['POST'])
# def trigger_scan():
#     # placeholder scan trigger
#     return {"status": "scan started"}
