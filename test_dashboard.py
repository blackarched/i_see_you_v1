import os
import sys
import pytest

# Ensure project root (repo) is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Import the dashboard factory and validate core endpoints
from iseeyou import dashboard


def test_create_app_and_health_endpoint():
    """
    Basic smoke test: create the Flask app via the factory, check /health endpoint.
    This verifies the app factory runs without external services required.
    """
    app = dashboard.create_app()
    client = app.test_client()
    rv = client.get("/health")
    assert rv.status_code == 200
    # Accept simple 'ok' or JSON {"status":"ok"} patterns
    body = rv.get_data(as_text=True).lower()
    assert "ok" in body or '"status"' in body