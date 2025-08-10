// components/dashboard/LiveTerminal.jsx
import React, { useEffect, useRef, useState } from "react";
import { WS_BASE } from "../../config";

export default function LiveTerminal({ sessionId, token }) {
  const [lines, setLines] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!sessionId) return;

    const wsUrl = `${WS_BASE}/terminal/${sessionId}?token=${encodeURIComponent(token || "")}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    ws.onopen = () => console.log("terminal ws open");
    ws.onmessage = (evt) => {
      try {
        const data = typeof evt.data === "string" ? JSON.parse(evt.data) : evt.data;
        setLines(prev => [...prev, data.line || evt.data]);
      } catch {
        setLines(prev => [...prev, evt.data]);
      }
    };
    ws.onclose = () => console.log("terminal ws closed");
    ws.onerror = (e) => console.error("terminal ws error", e);

    return () => {
      try { ws.close(); } catch {}
    };
  }, [sessionId, token]);

  return (
    <div className="live-terminal">
      <pre>
        {lines.map((l, idx) => <div key={idx}>{l}</div>)}
      </pre>
    </div>
  );
}