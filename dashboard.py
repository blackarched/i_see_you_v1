"""
dashboard.py (Corrected & Extended)
- Includes new endpoints under /api/attack/ to securely trigger backend scripts.
- Validates all user-provided input before passing to shell commands.
"""
import os
import time
import hmac
import hashlib
import json
import logging
import subprocess
import shlex
from functools import wraps
import bcrypt
from flask import (
    Flask,
    request,
    jsonify,
    make_response,
    Response,
    render_template,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

try:
    import redis as redislib
except ImportError:
    redislib = None

# --- Configuration & Globals ---
SECRET = os.environ.get('ISEEYOU_SECRET', 'dev-secret-do-not-use-in-prod')
ADMIN_USER = os.environ.get("ISEEYOU_ADMIN_USER", "admin")
ADMIN_PASS_HASH = os.environ.get("ISEEYOU_ADMIN_PASS_HASH")
LOG_FILE_PATH = os.environ.get("ISEEYOU_LOG_FILE", "iseeyou.log")
REDIS_URL = os.environ.get("REDIS_URL")
SCRIPTS_PATH = os.environ.get("SCRIPTS_PATH", "./scripts")

if not ADMIN_PASS_HASH and os.environ.get('ENV') == 'production':
    raise RuntimeError("ISEEYOU_ADMIN_PASS_HASH must be set in production.")

_SCANNER = None
_device_db = None
_redis_client = None
if REDIS_URL and redislib:
    try:
        _redis_client = redislib.Redis.from_url(REDIS_URL, decode_responses=True)
        _redis_client.ping()
        logging.info("Connected to Redis for sessions and Pub/Sub.")
    except Exception as e:
        logging.warning("Could not connect to Redis: %s.", e)
        _redis_client = None

# --- Authentication & Broadcasting Helpers ---
def issue_session_token(user_id: str) -> str:
    exp = int(time.time()) + 3600
    payload = f"{user_id}:{exp}"
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"

def verify_session_token(token: str) -> str | None:
    try:
        user, exp_s, sig = token.rsplit(":", 2)
        expected = hmac.new(SECRET.encode(), f"{user}:{exp_s}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig) or int(exp_s) < time.time():
            return None
        return user
    except (ValueError, TypeError):
        return None

def require_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.cookies.get("iseeyou_session")
        if not token or not verify_session_token(token):
            return jsonify({"error": "unauthenticated"}), 401
        return func(*args, **kwargs)
    return wrapper

def broadcast_device_update(device: dict):
    if _redis_client:
        try:
            event_data = json.dumps({"type": "device_update", "device": device})
            _redis_client.publish("iseeyou_events", event_data)
        except Exception as e:
            logging.error("Failed to publish device update to Redis: %s", e)

# --- Secure Script Execution Helper ---
def execute_script(script_name, args):
    script_path = os.path.join(SCRIPTS_PATH, script_name)
    if not os.path.isfile(script_path) or not os.access(script_path, os.X_OK):
        logging.error("Script not found or not executable: %s", script_path)
        return False, "Script not found on server."

    try:
        sanitized_args = [shlex.quote(str(arg)) for arg in args]
        command = [script_path] + sanitized_args
        logging.info("Executing command: %s", " ".join(command))
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, f"{script_name} started successfully."
    except Exception as e:
        logging.exception("Failed to execute script %s", script_name)
        return False, str(e)

# --- Flask App Factory ---
def create_app(device_database, attach_shutdown_event=None) -> Flask:
    global _device_db
    _device_db = device_database
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.secret_key = SECRET

    limiter = Limiter(key_func=get_remote_address)
    limiter.init_app(app)

    @app.route("/")
    @require_session
    def index():
        return render_template("aura_dashboard.html")

    @app.route("/api/login", methods=["POST"])
    def login():
        data = request.get_json()
        username = data.get("username")
        password = data.get("password", "").encode()

        if username == ADMIN_USER and ADMIN_PASS_HASH:
            if bcrypt.checkpw(password, ADMIN_PASS_HASH.encode()):
                token = issue_session_token(username)
                resp = make_response(jsonify({"message": "ok"}))
                resp.set_cookie("iseeyou_session", token, httponly=True, secure=True, samesite="Strict")
                return resp

        return jsonify({"error": "invalid credentials"}), 401
    
    @app.route("/logout", methods=["POST"])
    def logout():
        resp = make_response(jsonify({"message": "logged out"}))
        resp.delete_cookie("iseeyou_session")
        return resp

    @app.route("/health")
    def health():
        return jsonify({"ok": True, "scanner": "attached" if _SCANNER else "missing"})

    @app.route("/api/devices", methods=["GET"])
    @require_session
    def get_devices():
        """Get list of discovered devices"""
        try:
            devices = []
            if hasattr(_device_db, 'items'):
                devices = [device for ip, device in _device_db.items()]
            elif hasattr(_device_db, 'keys'):
                devices = [_device_db.get(ip) for ip in _device_db.keys()]

            # Sort by last seen
            devices.sort(key=lambda x: x.get('last_seen', 0), reverse=True)
            return jsonify({"devices": devices})
        except Exception as e:
            logging.error(f"Error fetching devices: {str(e)}")
            return jsonify({"error": "Failed to fetch devices"}), 500

    @app.route("/api/scan", methods=["POST"])
    @require_session
    def api_scan():
        if not _SCANNER:
            return jsonify({"error": "scanner not attached"}), 503

        try:
            started = _SCANNER.trigger_scan()
            return jsonify({"started": bool(started)})
        except Exception as e:
            logging.error(f"Scan trigger error: {str(e)}")
            return jsonify({"error": "Failed to start scan"}), 500

    @app.route("/api/logs", methods=["GET"])
    @require_session
    def api_logs():
        try:
            with open(LOG_FILE_PATH, 'r') as f:
                return jsonify(f.readlines()[-50:])
        except Exception as e:
            return jsonify([f"ERROR: Could not read log file."])

    @app.route("/events")
    @require_session
    def sse_events():
        if not _redis_client:
            return Response("data: {\"error\": \"Redis not configured\"}\n\n", mimetype="text/event-stream")
        def gen():
            pubsub = _redis_client.pubsub()
            pubsub.subscribe("iseeyou_events")
            try:
                snapshot = [v for k, v in _device_db.items()]
                yield f"event: snapshot\ndata: {json.dumps(snapshot)}\n\n"
            except Exception as e:
                logging.error("Error sending SSE snapshot: %s", e)
            for message in pubsub.listen():
                if message['type'] == 'message':
                    event_data = json.loads(message['data'])
                    yield f"event: {event_data['type']}\ndata: {json.dumps(event_data)}\n\n"
        return Response(gen(), mimetype="text/event-stream")

    @app.route("/api/attack/<module_name>", methods=["POST"])
    @require_session
    def handle_attack(module_name):
        """Handle attack module execution with advanced optimization and monitoring"""
        from attack_manager import AttackManager

        attack_mgr = AttackManager()
        data = request.get_json()

        if not data:
            return jsonify({"status": "error", "error": "Invalid JSON"}), 400

        # Prepare target information for intelligent optimization
        target_info = {
            'bssid': data.get('bssid'),
            'channel': data.get('channel'),
            'signal_strength': data.get('signal_strength'),
            'encryption': data.get('encryption'),
            'client_count': data.get('client_count', 0),
            'wps_enabled': data.get('wps_enabled', False),
            'wordlist': data.get('wordlist')
        }

        # Execute attack with advanced optimization
        result = attack_mgr.execute_attack(module_name, data, target_info)

        if result['success']:
            return jsonify({
                "status": "ok",
                "message": result['message'],
                "attack_id": result.get('attack_id'),
                "pid": result.get('pid'),
                "optimizations_applied": result.get('optimizations_applied', []),
                "recommendations": result.get('recommendations', [])
            })
        else:
            return jsonify({"status": "error", "error": result['error']}), 500

    @app.route("/api/attack/status", methods=["GET"])
    @require_session
    def get_attack_status():
        """Get attack system status"""
        from attack_manager import AttackManager

        attack_mgr = AttackManager()
        status = attack_mgr.get_attack_status()
        return jsonify(status)

    @app.route("/api/attack/stop/<int:pid>", methods=["POST"])
    @require_session
    def stop_attack(pid):
        """Stop a running attack process"""
        from attack_manager import AttackManager

        attack_mgr = AttackManager()
        success = attack_mgr.stop_attack(pid)

        if success:
            return jsonify({"status": "ok", "message": f"Attack process {pid} stopped"})
        else:
            return jsonify({"status": "error", "error": "Failed to stop attack process"}), 500

    @app.route("/api/attack/progress/<attack_id>", methods=["GET"])
    @require_session
    def get_attack_progress(attack_id):
        """Get real-time progress of a specific attack"""
        from attack_manager import AttackManager

        attack_mgr = AttackManager()
        progress = attack_mgr.get_attack_progress(attack_id)

        if progress:
            return jsonify({"status": "ok", "progress": progress})
        else:
            return jsonify({"status": "error", "error": "Attack not found"}), 404

    @app.route("/api/attack/analytics", methods=["GET"])
    @require_session
    def get_attack_analytics():
        """Get comprehensive attack analytics"""
        from attack_manager import AttackManager

        attack_mgr = AttackManager()
        analytics = attack_mgr.get_attack_analytics()
        return jsonify({"status": "ok", "analytics": analytics})

    @app.route("/api/attack/suggestions", methods=["POST"])
    @require_session
    def get_attack_suggestions():
        """Get intelligent attack suggestions for a target"""
        from attack_manager import AttackManager

        attack_mgr = AttackManager()
        data = request.get_json()

        if not data:
            return jsonify({"status": "error", "error": "Invalid JSON"}), 400

        suggestions = attack_mgr.get_smart_suggestions(data)
        return jsonify({"status": "ok", "suggestions": suggestions})

    @app.route("/api/attack/recommendations/<module>", methods=["POST"])
    @require_session
    def get_attack_recommendations(module):
        """Get specific recommendations for an attack module"""
        from attack_manager import AttackManager

        attack_mgr = AttackManager()
        data = request.get_json() or {}

        recommendations = attack_mgr.get_attack_recommendations(module, data)
        return jsonify({"status": "ok", "recommendations": recommendations})

    @app.route("/api/interfaces", methods=["GET"])
    @require_session
    def get_wireless_interfaces():
        """Get information about available wireless interfaces"""
        from attack_manager import AttackManager

        attack_mgr = AttackManager()
        interfaces = attack_mgr.wireless_interfaces
        return jsonify({"status": "ok", "interfaces": interfaces})

    return app

def register_monitor(monitor):
    """Register the passive monitor instance"""
    global _MONITOR
    _MONITOR = monitor

def register_scanner(scanner):
    global _SCANNER
    _SCANNER = scanner

def shutdown_components(timeout=5):
    """Cleanly shutdown dashboard components"""
    global _MONITOR, _SCANNER
    errors = []
    
    try:
        if _MONITOR and hasattr(_MONITOR, 'stop'):
            _MONITOR.stop()
    except Exception as e:
        errors.append(f"Error stopping monitor: {e}")
    
    try:
        if _SCANNER and hasattr(_SCANNER, 'stop'):
            _SCANNER.stop()
    except Exception as e:
        errors.append(f"Error stopping scanner: {e}")
    
    return errors