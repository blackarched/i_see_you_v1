pages/Dashboard.js

import React, { useState, useEffect } from "react";
import { Device, SystemHealth, NetworkLog } from "@/entities/all";

import EnhancedHudHeader from "../components/dashboard/EnhancedHudHeader";
import SystemStatusPanel from "../components/dashboard/SystemStatusPanel";
import DeviceGrid from "../components/dashboard/DeviceGrid";
import NetworkMetrics from "../components/dashboard/NetworkMetrics";
import LiveTerminal from "../components/dashboard/LiveTerminal";
import ThreatAnalysis from "../components/dashboard/ThreatAnalysis";
import ScanControls from "../components/dashboard/ScanControls";
import AnimatedRobot from "../components/dashboard/AnimatedRobot";
import FloatingMenu from "../components/dashboard/FloatingMenu";

export default function Dashboard() {
  const [devices, setDevices] = useState([]);
  const [systemHealth, setSystemHealth] = useState([]);
  const [networkLogs, setNetworkLogs] = useState([]);
  const [isScanning, setIsScanning] = useState(false);
  const [lastScanTime, setLastScanTime] = useState(new Date());
  const [showFloatingMenu, setShowFloatingMenu] = useState(false);

  useEffect(() => {
    loadInitialData();
    
    // Simulate real-time updates
    const interval = setInterval(() => {
      updateRealTimeData();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const loadInitialData = async () => {
    const [devicesData, healthData, logsData] = await Promise.all([
      Device.list('-last_seen', 50),
      SystemHealth.list('-created_date', 10),
      NetworkLog.list('-timestamp', 100)
    ]);
    
    setDevices(devicesData);
    setSystemHealth(healthData);
    setNetworkLogs(logsData);
  };

  const updateRealTimeData = async () => {
    // Simulate device status updates
    setDevices(prev => prev.map(device => ({
      ...device,
      response_time: Math.random() * 100 + 10,
      status: Math.random() > 0.9 ? 'warning' : 'online'
    })));

    // Add new log entry occasionally
    if (Math.random() > 0.7) {
      const newLog = {
        timestamp: new Date().toISOString(),
        level: ['INFO', 'WARNING', 'DEBUG'][Math.floor(Math.random() * 3)],
        service: 'NetworkScanner',
        message: `Device scan completed - ${Math.floor(Math.random() * 20) + 10} devices active`,
        event_type: 'scan'
      };
      
      try {
        await NetworkLog.create(newLog);
        setNetworkLogs(prev => [newLog, ...prev.slice(0, 99)]);
      } catch (error) {
        console.log('Log creation simulation');
      }
    }
  };

  const handleScanTrigger = async () => {
    setIsScanning(true);
    setLastScanTime(new Date());
    
    // Simulate scan process
    setTimeout(() => {
      setIsScanning(false);
      updateRealTimeData();
    }, 3000);
  };

  return (
    <div className="min-h-screen p-4 md:p-6 space-y-6 relative">
      {/* Animated Robots */}
      <AnimatedRobot type="scanner" position="bottom-left" size="medium" />
      <AnimatedRobot type="guard" position="bottom-right" size="small" />
      <AnimatedRobot type="analyst" position="top-right" size="medium" />
      
      <EnhancedHudHeader 
        deviceCount={devices.length}
        onlineDevices={devices.filter(d => d.status === 'online').length}
        lastScanTime={lastScanTime}
        isScanning={isScanning}
      />
      
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column - System Status */}
        <div className="lg:col-span-1 space-y-6">
          <SystemStatusPanel systemHealth={systemHealth} />
          <ScanControls 
            onScanTrigger={handleScanTrigger}
            isScanning={isScanning}
            onOpenMenu={() => setShowFloatingMenu(true)}
          />
          <ThreatAnalysis devices={devices} />
        </div>

        {/* Middle Column - Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <DeviceGrid devices={devices} />
          <NetworkMetrics devices={devices} />
        </div>

        {/* Right Column - Live Data */}
        <div className="lg:col-span-1">
          <LiveTerminal logs={networkLogs} />
        </div>
      </div>

      {/* Floating Menu */}
      <FloatingMenu 
        isVisible={showFloatingMenu}
        onClose={() => setShowFloatingMenu(false)}
      />
    </div>
  );
}