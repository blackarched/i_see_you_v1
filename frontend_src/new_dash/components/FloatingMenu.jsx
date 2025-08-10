components/dashboard/FloatingMenu.jsx

import React, { useState, useEffect } from "react";
import { Settings, Zap, Shield, Eye, Target, Wifi, Lock, Globe } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function FloatingMenu({ isVisible, onClose }) {
  const [activeSection, setActiveSection] = useState("scan");
  const [hoveredItem, setHoveredItem] = useState(null);

  const menuSections = {
    scan: {
      title: "SCAN OPTIONS",
      color: "cyan",
      items: [
        { id: "quick", label: "Quick Scan", icon: Zap, description: "Fast network discovery" },
        { id: "deep", label: "Deep Scan", icon: Target, description: "Comprehensive analysis" },
        { id: "stealth", label: "Stealth Mode", icon: Eye, description: "Silent reconnaissance" }
      ]
    },
    security: {
      title: "SECURITY",
      color: "red",
      items: [
        { id: "firewall", label: "Firewall", icon: Shield, description: "Network protection" },
        { id: "intrusion", label: "IDS Monitor", icon: Lock, description: "Intrusion detection" },
        { id: "threat", label: "Threat Intel", icon: Globe, description: "Global threat data" }
      ]
    },
    network: {
      title: "NETWORK",
      color: "green",
      items: [
        { id: "topology", label: "Topology", icon: Wifi, description: "Network mapping" },
        { id: "bandwidth", label: "Bandwidth", icon: Target, description: "Traffic analysis" },
        { id: "quality", label: "QoS Monitor", icon: Settings, description: "Service quality" }
      ]
    }
  };

  const getColorClasses = (color) => {
    const colors = {
      cyan: "border-cyan-400 text-cyan-400 bg-cyan-400/10 hover:bg-cyan-400/20",
      red: "border-red-400 text-red-400 bg-red-400/10 hover:bg-red-400/20",
      green: "border-green-400 text-green-400 bg-green-400/10 hover:bg-green-400/20"
    };
    return colors[color] || colors.cyan;
  };

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <motion.div
        initial={{ scale: 0, rotate: -180 }}
        animate={{ scale: 1, rotate: 0 }}
        exit={{ scale: 0, rotate: 180 }}
        className="bg-black/90 border-2 border-cyan-400/50 rounded-xl p-8 max-w-4xl w-full mx-4 backdrop-blur-xl relative overflow-hidden"
      >
        {/* Background effects */}
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-400/5 via-transparent to-purple-400/5" />
        
        {/* Header */}
        <div className="flex items-center justify-between mb-8 relative z-10">
          <h2 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent font-mono">
            COMMAND CENTER
          </h2>
          <button
            onClick={onClose}
            className="text-red-400 hover:text-red-300 transition-colors text-2xl font-bold"
          >
            ×
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 relative z-10">
          {/* Section tabs */}
          <div className="lg:col-span-1 space-y-2">
            {Object.entries(menuSections).map(([key, section]) => (
              <button
                key={key}
                onClick={() => setActiveSection(key)}
                className={`w-full text-left p-4 rounded-lg border-2 font-mono text-sm transition-all duration-300 ${
                  activeSection === key 
                    ? getColorClasses(section.color)
                    : 'border-gray-600 text-gray-400 hover:border-gray-500'
                }`}
              >
                {section.title}
              </button>
            ))}
          </div>

          {/* Active section content */}
          <div className="lg:col-span-3">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeSection}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                <h3 className={`text-xl font-bold font-mono ${getColorClasses(menuSections[activeSection].color).split(' ')[1]}`}>
                  {menuSections[activeSection].title}
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {menuSections[activeSection].items.map((item) => {
                    const IconComponent = item.icon;
                    return (
                      <motion.button
                        key={item.id}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onHoverStart={() => setHoveredItem(item.id)}
                        onHoverEnd={() => setHoveredItem(null)}
                        className={`p-4 rounded-lg border-2 text-left transition-all duration-300 ${getColorClasses(menuSections[activeSection].color)}`}
                      >
                        <div className="flex items-start gap-3">
                          <IconComponent className="w-6 h-6 flex-shrink-0 mt-1" />
                          <div>
                            <h4 className="font-bold font-mono">{item.label}</h4>
                            <p className="text-xs opacity-70 mt-1">{item.description}</p>
                          </div>
                        </div>
                        
                        {hoveredItem === item.id && (
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: "100%" }}
                            className="mt-3 h-0.5 bg-current rounded-full"
                          />
                        )}
                      </motion.button>
                    );
                  })}
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        {/* Decorative elements */}
        <div className="absolute top-4 left-4 w-6 h-6 border-l-2 border-t-2 border-cyan-400 opacity-50" />
        <div className="absolute top-4 right-4 w-6 h-6 border-r-2 border-t-2 border-cyan-400 opacity-50" />
        <div className="absolute bottom-4 left-4 w-6 h-6 border-l-2 border-b-2 border-cyan-400 opacity-50" />
        <div className="absolute bottom-4 right-4 w-6 h-6 border-r-2 border-b-2 border-cyan-400 opacity-50" />
      </motion.div>
    </div>
  );
}