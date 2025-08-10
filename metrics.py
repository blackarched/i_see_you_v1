
"""
Centralized Prometheus metrics helpers.
If prometheus_client is not available, provides noop stubs.
"""
try:
    from prometheus_client import Counter, Histogram
    # define metrics
    METRICS_SCAN_DURATION = Histogram('iseeyou_scan_duration_seconds', 'Active scan duration in seconds')
    METRICS_SCAN_ERRORS = Counter('iseeyou_scan_errors_total', 'Errors during active scanning')
    METRICS_DEVICE_ADDITIONS = Counter('iseeyou_device_additions_total', 'Count of newly discovered devices')
except Exception:
    # Define no-op stubs
    class _Noop:
        def inc(self, *a, **k): pass
        def observe(self, *a, **k): pass
    METRICS_SCAN_DURATION = _Noop()
    METRICS_SCAN_ERRORS = _Noop()
    METRICS_DEVICE_ADDITIONS = _Noop()
