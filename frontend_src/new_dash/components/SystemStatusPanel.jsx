// components/dashboard/SystemStatusPanel.jsx
import React, { useEffect, useState } from "react";
import { get } from "../../lib/api";

export default function SystemStatusPanel({ token }) {
  const [health, setHealth] = useState(null);
  useEffect(() => {
    let mounted = true;
    get("/health", { token }).then(h => { if (mounted) setHealth(h); }).catch(console.error);
    return () => { mounted = false; };
  }, [token]);

  if (!health) return <div>Loading health…</div>;
  return (
    <div>
      <h4>System Health</h4>
      <div>Uptime: {health.uptime}</div>
      <div>CPU: {health.cpu_load}</div>
      <div>Memory: {health.memory_used}/{health.memory_total}</div>
    </div>
  );
}