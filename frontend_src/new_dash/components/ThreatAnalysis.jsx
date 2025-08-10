components/dashboard/ThreatAnalysis.jsx

import React from "react";
import { Shield, AlertTriangle, Zap, Eye } from "lucide-react";

export default function ThreatAnalysis({ devices }) {
  const threatData = {
    total: devices.length || 64,
    safe: Math.floor((devices.length || 64) * 0.7),
    warnings: Math.floor((devices.length || 64) * 0.2),
    critical: Math.floor((devices.length || 64) * 0.1),
    blocked: Math.floor(Math.random() * 50) + 20
  };

  const recentThreats = [
    { ip: '192.168.1.152', type: 'Port Scan', level: 'medium', time: '2m ago' },
    { ip: '192.168.1.89', type: 'Suspicious Traffic', level: 'low', time: '5m ago' },
    { ip: '192.168.1.200', type: 'Auth Failure', level: 'high', time: '8m ago' },
    { ip: '192.168.1.45', type: 'DDoS Attempt', level: 'critical', time: '12m ago' }
  ];

  const getThreatColor = (level) => {
    const colors = {
      low: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
      medium: 'text-orange-400 bg-orange-400/10 border-orange-400/30',
      high: 'text-red-400 bg-red-400/10 border-red-400/30',
      critical: 'text-pink-500 bg-pink-500/10 border-pink-500/50'
    };
    return colors[level] || 'text-gray-400 bg-gray-400/10 border-gray-400/30';
  };

  return (
    <div className="relative bg-black/60 backdrop-blur-lg border border-red-400/30 rounded-lg p-4 shadow-2xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4 border-b border-red-400/20 pb-3">
        <Shield className="w-6 h-6 text-red-400 animate-pulse" />
        <h3 className="text-xl font-bold text-red-400 font-mono">THREAT ANALYSIS</h3>
      </div>

      {/* Threat Summary */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-black/40 rounded-md p-3 border border-green-400/30">
          <div className="flex items-center justify-between">
            <span className="text-green-400 text-xs font-mono">SAFE</span>
            <Shield className="w-4 h-4 text-green-400" />
          </div>
          <div className="text-green-400 text-xl font-bold font-mono">{threatData.safe}</div>
        </div>

        <div className="bg-black/40 rounded-md p-3 border border-yellow-400/30">
          <div className="flex items-center justify-between">
            <span className="text-yellow-400 text-xs font-mono">WARNINGS</span>
            <AlertTriangle className="w-4 h-4 text-yellow-400" />
          </div>
          <div className="text-yellow-400 text-xl font-bold font-mono">{threatData.warnings}</div>
        </div>

        <div className="bg-black/40 rounded-md p-3 border border-red-400/30">
          <div className="flex items-center justify-between">
            <span className="text-red-400 text-xs font-mono">CRITICAL</span>
            <Zap className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-red-400 text-xl font-bold font-mono">{threatData.critical}</div>
        </div>

        <div className="bg-black/40 rounded-md p-3 border border-pink-400/30">
          <div className="flex items-center justify-between">
            <span className="text-pink-400 text-xs font-mono">BLOCKED</span>
            <Eye className="w-4 h-4 text-pink-400" />
          </div>
          <div className="text-pink-400 text-xl font-bold font-mono">{threatData.blocked}</div>
        </div>
      </div>

      {/* Recent Threats */}
      <div className="space-y-2">
        <h4 className="text-red-300 font-mono text-sm mb-2 border-b border-red-400/20 pb-1">
          RECENT THREATS
        </h4>
        
        {recentThreats.map((threat, index) => (
          <div key={index} className="bg-black/40 rounded-md p-2 border border-gray-700/50 hover:border-red-400/30 transition-colors">
            <div className="flex items-center justify-between mb-1">
              <span className="text-cyan-400 font-mono text-xs">{threat.ip}</span>
              <span className="text-gray-400 text-xs">{threat.time}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-white text-xs">{threat.type}</span>
              <span className={`px-2 py-1 rounded text-xs font-mono border ${getThreatColor(threat.level)}`}>
                {threat.level.toUpperCase()}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Security Status Indicator */}
      <div className="mt-4 p-3 bg-black/40 rounded-md border border-green-400/30">
        <div className="flex items-center justify-between">
          <span className="text-green-400 font-mono text-sm">SECURITY STATUS</span>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-green-400 font-mono text-sm">PROTECTED</span>
          </div>
        </div>
      </div>

      {/* Corner brackets */}
      <div className="absolute top-2 left-2 w-4 h-4 border-l-2 border-t-2 border-red-400" />
      <div className="absolute top-2 right-2 w-4 h-4 border-r-2 border-t-2 border-red-400" />
      <div className="absolute bottom-2 left-2 w-4 h-4 border-l-2 border-b-2 border-red-400" />
      <div className="absolute bottom-2 right-2 w-4 h-4 border-r-2 border-b-2 border-red-400" />
    </div>
  );
}
