// components/dashboard/DeviceGrid.jsx
import React, { useEffect, useState } from "react";
import { get, post } from "../../lib/api";

export default function DeviceGrid({ token }) {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    get("/devices", { token })
      .then(data => { if (mounted) setDevices(data.devices || data); })
      .catch(console.error)
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [token]);

  const reboot = async (deviceId) => {
    try {
      // optimistic UI update (toggle busy)
      await post(`/devices/${deviceId}/reboot`, {}, { token });
      // refresh list
      const data = await get("/devices", { token });
      setDevices(data.devices || data);
    } catch (e) {
      console.error(e);
      alert("Failed to reboot device");
    }
  };

  if (loading) return <div>Loading devices…</div>;
  return (
    <div className="device-grid">
      {devices.map(d => (
        <div key={d.id} className="device-card">
          <div className="name">{d.name}</div>
          <div className="ip">{d.ip}</div>
          <div className="status">{d.status}</div>
          <button onClick={() => reboot(d.id)}>Reboot</button>
        </div>
      ))}
    </div>
  );
}