components/dashboard/EnhancedHudHeader.jsx

import React, { useState, useEffect } from "react";
import { Shield, Zap, Clock, Wifi, Settings, Bell, Search, Menu } from "lucide-react";
import { format } from "date-fns";

export default function EnhancedHudHeader({ deviceCount, onlineDevices, lastScanTime, isScanning }) {
  const [showSubMenu, setShowSubMenu] = useState(false);
  const [notifications, setNotifications] = useState(3);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [systemLoad, setSystemLoad] = useState(45);

  useEffect(() => {
    const timeInterval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    const loadInterval = setInterval(() => {
      setSystemLoad(prev => Math.max(20, Math.min(80, prev + (Math.random() - 0.5) * 10)));
    }, 2000);

    return () => {
      clearInterval(timeInterval);
      clearInterval(loadInterval);
    };
  }, []);

  return (
    <div className="relative">
      {/* Enhanced main header panel */}
      <div className="bg-black/50 backdrop-blur-xl border-2 border-cyan-400/40 rounded-xl p-6 shadow-2xl relative overflow-hidden">
        {/* Animated background pattern */}
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400/5 to-transparent animate-pulse" />
        
        {/* Top status bar */}
        <div className="flex items-center justify-between mb-4 text-xs font-mono">
          <div className="flex items-center gap-4">
            <span className="text-green-400">SYS.LOAD: {systemLoad.toFixed(1)}%</span>
            <span className="text-yellow-400">UPTIME: 127:43:22</span>
            <span className="text-cyan-400">NET.STATUS: OPTIMAL</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-pink-400">{format(currentTime, 'yyyy.MM.dd')}</span>
            <span className="text-white">{format(currentTime, 'HH:mm:ss')}</span>
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-yellow-400" />
              {notifications > 0 && (
                <span className="bg-red-500 text-white rounded-full px-1.5 py-0.5 text-xs animate-pulse">
                  {notifications}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          {/* Enhanced Title Section */}
          <div className="flex items-center gap-4 relative">
            <div className="relative group">
              <Shield className="w-12 h-12 text-pink-400 neon-text relative z-10" />
              <div className="absolute inset-0 animate-ping">
                <Shield className="w-12 h-12 text-pink-400 opacity-20" />
              </div>
              <div className="absolute inset-0 animate-pulse">
                <Shield className="w-12 h-12 text-cyan-400 opacity-30" />
              </div>
            </div>
            <div>
              <h1 className="text-4xl lg:text-5xl font-bold bg-gradient-to-r from-pink-400 via-cyan-400 to-green-400 bg-clip-text text-transparent neon-text relative">
                ISeeYou Network Monitor
                <div className="absolute -inset-1 bg-gradient-to-r from-pink-400/20 via-cyan-400/20 to-green-400/20 blur-xl opacity-50 animate-pulse" />
              </h1>
              <div className="flex items-center gap-4 mt-2">
                <p className="text-cyan-300 font-mono text-sm animate-pulse">
                  [ NEURAL INTERFACE ACTIVE - SCANNING GRID ]
                </p>
                <div className="flex gap-1">
                  {Array.from({length: 8}).map((_, i) => (
                    <div
                      key={i}
                      className="w-1 h-4 bg-green-400 animate-pulse"
                      style={{
                        animationDelay: `${i * 0.1}s`,
                        opacity: 0.3 + (i * 0.1)
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Enhanced Status Indicators with animations */}
          <div className="flex flex-wrap gap-4 lg:gap-6">
            <div className="relative group">
              <div className="bg-black/60 border-2 border-green-400/50 rounded-lg p-4 transition-all duration-300 hover:border-green-400 hover:shadow-lg hover:shadow-green-400/20">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Wifi className="w-6 h-6 text-green-400 animate-pulse" />
                  <span className="text-3xl font-bold text-green-400 neon-text">{deviceCount}</span>
                </div>
                <p className="text-green-300 text-xs font-mono text-center">DEVICES</p>
                <div className="absolute -inset-0.5 bg-green-400/20 rounded-lg blur opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              </div>
            </div>
            
            <div className="relative group">
              <div className="bg-black/60 border-2 border-yellow-400/50 rounded-lg p-4 transition-all duration-300 hover:border-yellow-400 hover:shadow-lg hover:shadow-yellow-400/20">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Zap className="w-6 h-6 text-yellow-400 animate-bounce" />
                  <span className="text-3xl font-bold text-yellow-400 neon-text">{onlineDevices}</span>
                </div>
                <p className="text-yellow-300 text-xs font-mono text-center">ONLINE</p>
                <div className="absolute -inset-0.5 bg-yellow-400/20 rounded-lg blur opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              </div>
            </div>
            
            <div className="relative group">
              <div className="bg-black/60 border-2 border-pink-400/50 rounded-lg p-4 transition-all duration-300 hover:border-pink-400 hover:shadow-lg hover:shadow-pink-400/20">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <Clock className="w-6 h-6 text-pink-400 animate-spin" style={{animationDuration: '4s'}} />
                  <span className="text-sm font-bold text-pink-400 font-mono">
                    {format(lastScanTime, 'HH:mm')}
                  </span>
                </div>
                <p className="text-pink-300 text-xs font-mono text-center">LAST SCAN</p>
                <div className="absolute -inset-0.5 bg-pink-400/20 rounded-lg blur opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              </div>
            </div>

            {/* Quick actions menu */}
            <div className="relative">
              <button
                onClick={() => setShowSubMenu(!showSubMenu)}
                className="bg-black/60 border-2 border-purple-400/50 rounded-lg p-4 transition-all duration-300 hover:border-purple-400 hover:shadow-lg hover:shadow-purple-400/20 group"
              >
                <Menu className="w-6 h-6 text-purple-400 group-hover:animate-spin" />
                <p className="text-purple-300 text-xs font-mono text-center mt-2">MENU</p>
              </button>

              {/* Sub menu */}
              {showSubMenu && (
                <div className="absolute top-full right-0 mt-2 bg-black/90 border border-purple-400/50 rounded-lg p-2 min-w-48 z-50 backdrop-blur-xl">
                  <div className="space-y-1">
                    <button className="w-full text-left px-3 py-2 text-sm font-mono text-cyan-400 hover:bg-cyan-400/20 rounded flex items-center gap-2">
                      <Search className="w-4 h-4" />
                      Deep Scan
                    </button>
                    <button className="w-full text-left px-3 py-2 text-sm font-mono text-green-400 hover:bg-green-400/20 rounded flex items-center gap-2">
                      <Shield className="w-4 h-4" />
                      Security Check
                    </button>
                    <button className="w-full text-left px-3 py-2 text-sm font-mono text-yellow-400 hover:bg-yellow-400/20 rounded flex items-center gap-2">
                      <Settings className="w-4 h-4" />
                      System Config
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Enhanced scanning indicator */}
        {isScanning && (
          <div className="mt-6 relative">
            <div className="flex items-center gap-4 mb-3">
              <div className="w-4 h-4 bg-cyan-400 rounded-full animate-pulse shadow-lg shadow-cyan-400/50" />
              <span className="text-cyan-400 font-mono text-sm animate-pulse">
                ACTIVE DEEP SCAN IN PROGRESS - ANALYZING NETWORK TOPOLOGY...
              </span>
              <div className="flex gap-1">
                {Array.from({length: 5}).map((_, i) => (
                  <div
                    key={i}
                    className="w-1 h-6 bg-cyan-400 animate-pulse"
                    style={{
                      animationDelay: `${i * 0.2}s`,
                      animationDuration: '1s'
                    }}
                  />
                ))}
              </div>
            </div>
            <div className="relative bg-gray-800/50 rounded-full h-2 overflow-hidden border border-cyan-400/30">
              <div 
                className="h-full bg-gradient-to-r from-cyan-400 via-green-400 to-pink-400 rounded-full animate-pulse relative"
                style={{width: '75%'}}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
              </div>
            </div>
            <div className="flex justify-between text-xs font-mono text-gray-400 mt-1">
              <span>Packet Analysis: 847/1203</span>
              <span>Threat Detection: Active</span>
              <span>ETA: 00:45</span>
            </div>
          </div>
        )}

        {/* Holographic corners */}
        <div className="absolute -top-1 -left-1 w-8 h-8 border-l-4 border-t-4 border-cyan-400 animate-pulse opacity-80" />
        <div className="absolute -top-1 -right-1 w-8 h-8 border-r-4 border-t-4 border-cyan-400 animate-pulse opacity-80" />
        <div className="absolute -bottom-1 -left-1 w-8 h-8 border-l-4 border-b-4 border-cyan-400 animate-pulse opacity-80" />
        <div className="absolute -bottom-1 -right-1 w-8 h-8 border-r-4 border-b-4 border-cyan-400 animate-pulse opacity-80" />
      </div>

      <style jsx>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
      `}</style>
    </div>
  );
}