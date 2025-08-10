// components/dashboard/ScanControls.jsx
import React, { useState } from "react";
import { post } from "../../lib/api";

export default function ScanControls({ token, onScanStarted }) {
  const [running, setRunning] = useState(false);
  const startScan = async () => {
    try {
      setRunning(true);
      const res = await post("/scan/start", {}, { token });
      onScanStarted && onScanStarted(res);
    } catch(e) {
      console.error(e);
      alert("Start scan failed");
      setRunning(false);
    }
  };
  const stopScan = async () => {
    try {
      const res = await post("/scan/stop", {}, { token });
      setRunning(false);
    } catch(e) {
      console.error(e);
      alert("Stop scan failed");
    }
  };
  return (
    <div>
      <button onClick={startScan} disabled={running}>Start Scan</button>
      <button onClick={stopScan} disabled={!running}>Stop Scan</button>
    </div>
  );
}