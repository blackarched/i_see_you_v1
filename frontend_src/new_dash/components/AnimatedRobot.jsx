components/dashboard/AnimatedRobot.jsx

import React, { useState, useEffect } from "react";
import { Zap, Eye, Wifi, Shield } from "lucide-react";

export default function AnimatedRobot({ type = "scanner", position = "bottom-left", size = "medium" }) {
  const [isActive, setIsActive] = useState(false);
  const [eyeGlow, setEyeGlow] = useState(false);
  const [antennaSignal, setAntennaSignal] = useState(0);

  useEffect(() => {
    const activityInterval = setInterval(() => {
      setIsActive(prev => !prev);
    }, 3000);

    const eyeInterval = setInterval(() => {
      setEyeGlow(prev => !prev);
    }, 2000);

    const signalInterval = setInterval(() => {
      setAntennaSignal(prev => (prev + 1) % 4);
    }, 800);

    return () => {
      clearInterval(activityInterval);
      clearInterval(eyeInterval);
      clearInterval(signalInterval);
    };
  }, []);

  const sizeClasses = {
    small: "w-12 h-16",
    medium: "w-16 h-20",
    large: "w-20 h-24"
  };

  const positionClasses = {
    "bottom-left": "bottom-4 left-4",
    "bottom-right": "bottom-4 right-4",
    "top-left": "top-4 left-4",
    "top-right": "top-4 right-4",
    "floating": "top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2"
  };

  const getRobotIcon = () => {
    switch(type) {
      case "scanner": return <Wifi className="w-3 h-3" />;
      case "guard": return <Shield className="w-3 h-3" />;
      case "analyst": return <Eye className="w-3 h-3" />;
      default: return <Zap className="w-3 h-3" />;
    }
  };

  const getRobotColor = () => {
    switch(type) {
      case "scanner": return "border-cyan-400 text-cyan-400";
      case "guard": return "border-red-400 text-red-400";
      case "analyst": return "border-purple-400 text-purple-400";
      default: return "border-green-400 text-green-400";
    }
  };

  return (
    <div className={`fixed ${positionClasses[position]} z-20 pointer-events-none`}>
      <div className={`${sizeClasses[size]} relative ${isActive ? 'animate-bounce' : ''}`}>
        {/* Robot Body */}
        <div className={`w-full h-3/4 bg-black/80 backdrop-blur-sm border-2 ${getRobotColor()} rounded-lg relative overflow-hidden`}>
          {/* Inner circuits */}
          <div className="absolute inset-1 bg-gradient-to-b from-transparent via-current/10 to-transparent rounded opacity-50" />
          
          {/* Eyes */}
          <div className="absolute top-2 left-1/2 transform -translate-x-1/2 flex gap-1">
            <div className={`w-1.5 h-1.5 rounded-full ${eyeGlow ? 'bg-red-400 shadow-lg shadow-red-400/50' : 'bg-gray-400'} transition-all duration-300`} />
            <div className={`w-1.5 h-1.5 rounded-full ${eyeGlow ? 'bg-red-400 shadow-lg shadow-red-400/50' : 'bg-gray-400'} transition-all duration-300`} />
          </div>

          {/* Chest display */}
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
            <div className={`p-1 border rounded ${getRobotColor()} bg-current/20`}>
              {getRobotIcon()}
            </div>
          </div>

          {/* Activity indicator */}
          <div className="absolute bottom-1 left-1/2 transform -translate-x-1/2">
            <div className={`w-1 h-1 rounded-full ${isActive ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
          </div>
        </div>

        {/* Robot Head/Antenna */}
        <div className="absolute -top-2 left-1/2 transform -translate-x-1/2">
          <div className={`w-1 h-3 bg-current rounded-full ${getRobotColor()}`} />
          <div className={`absolute -top-1 left-1/2 transform -translate-x-1/2 w-2 h-2 rounded-full border ${getRobotColor()} ${antennaSignal > 2 ? 'bg-current/50 shadow-lg shadow-current/50' : 'bg-transparent'}`} />
        </div>

        {/* Robot Arms */}
        <div className={`absolute top-1/4 -left-1 w-1 h-4 bg-current rounded ${getRobotColor()}`} />
        <div className={`absolute top-1/4 -right-1 w-1 h-4 bg-current rounded ${getRobotColor()}`} />

        {/* Robot Legs */}
        <div className={`absolute -bottom-1 left-1/4 w-1 h-3 bg-current rounded ${getRobotColor()}`} />
        <div className={`absolute -bottom-1 right-1/4 w-1 h-3 bg-current rounded ${getRobotColor()}`} />

        {/* Signal waves */}
        {antennaSignal > 0 && (
          <div className="absolute -top-6 left-1/2 transform -translate-x-1/2">
            {Array.from({length: antennaSignal}).map((_, i) => (
              <div
                key={i}
                className={`absolute border border-current rounded-full ${getRobotColor()}`}
                style={{
                  width: `${(i + 1) * 8}px`,
                  height: `${(i + 1) * 8}px`,
                  left: `${-(i + 1) * 4}px`,
                  top: `${-(i + 1) * 4}px`,
                  animation: `signal-pulse 2s ease-out infinite`,
                  animationDelay: `${i * 0.3}s`
                }}
              />
            ))}
          </div>
        )}

        <style jsx>{`
          @keyframes signal-pulse {
            0% { opacity: 0.8; transform: scale(0.5); }
            100% { opacity: 0; transform: scale(1.5); }
          }
        `}</style>
      </div>

      {/* Robot speech bubble (occasional) */}
      {isActive && Math.random() > 0.7 && (
        <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-black/90 border border-current rounded px-2 py-1 text-xs font-mono whitespace-nowrap animate-pulse">
          {type === "scanner" && "SCANNING..."}
          {type === "guard" && "SECURE"}
          {type === "analyst" && "ANALYZING"}
          {type === "helper" && "READY"}
        </div>
      )}
    </div>
  );
}