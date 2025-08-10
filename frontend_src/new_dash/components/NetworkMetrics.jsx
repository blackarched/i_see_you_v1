// components/dashboard/NetworkMetrics.jsx
import React, { useEffect, useState } from "react";
import { get } from "../../lib/api";

export default function NetworkMetrics({ token }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    get("/metrics", { token })
      .then(data => { if (mounted) setMetrics(data); })
      .catch(e => { if (mounted) setErr(e); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [token]);

  if (loading) return <div>Loading network metrics…</div>;
  if (err) return <div>Error loading metrics</div>;
  if (!metrics) return <div>No data</div>;

  // render metrics (adapt field names to your API shape)
  return (
    <div>
      <h3>Network Metrics</h3>
      <div>Throughput: {metrics.throughput ?? "—"}</div>
      <div>Active Connections: {metrics.connections ?? "—"}</div>
      <div>Alerts: {metrics.alerts ?? 0}</div>
    </div>
  );
}