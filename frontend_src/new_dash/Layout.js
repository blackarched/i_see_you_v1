Layout.js

import React from "react";
import { Link, useLocation } from "react-router-dom";
import { createPageUrl } from "@/utils";

export default function Layout({ children, currentPageName }) {
  return (
    <div className="min-h-screen bg-black relative overflow-hidden">
      {/* Enhanced Cyberpunk background effects */}
      <div className="fixed inset-0 bg-gradient-to-br from-black via-purple-900/20 to-black">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_50%,rgba(255,0,128,0.15),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,rgba(0,255,65,0.12),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_40%_80%,rgba(0,212,255,0.1),transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_60%,rgba(255,255,0,0.08),transparent_50%)]" />
      </div>
      
      {/* Enhanced Grid pattern with depth */}
      <div 
        className="fixed inset-0 opacity-30"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0,255,65,0.4) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,255,65,0.4) 1px, transparent 1px),
            linear-gradient(rgba(255,0,128,0.2) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,0,128,0.2) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px, 50px 50px, 100px 100px, 100px 100px'
        }}
      />
      
      {/* Multiple animated scan lines */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute w-full h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-70" 
             style={{ 
               animation: 'scan-vertical-1 8s linear infinite',
               top: '0%',
               boxShadow: '0 0 20px rgba(0,255,255,0.8)'
             }} />
        <div className="absolute w-full h-0.5 bg-gradient-to-r from-transparent via-pink-400 to-transparent opacity-50"
             style={{ 
               animation: 'scan-vertical-2 12s linear infinite',
               top: '0%',
               animationDelay: '4s'
             }} />
        <div className="absolute h-full w-1 bg-gradient-to-b from-transparent via-green-400 to-transparent opacity-60"
             style={{ 
               animation: 'scan-horizontal-1 10s linear infinite',
               left: '0%',
               boxShadow: '0 0 15px rgba(0,255,0,0.6)'
             }} />
        <div className="absolute h-full w-0.5 bg-gradient-to-b from-transparent via-yellow-400 to-transparent opacity-40"
             style={{ 
               animation: 'scan-horizontal-2 14s linear infinite',
               left: '0%',
               animationDelay: '3s'
             }} />
      </div>

      {/* Floating particles */}
      <div className="fixed inset-0 pointer-events-none">
        {Array.from({length: 20}).map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-cyan-400 rounded-full opacity-60"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animation: `float-particle-${i % 4} ${8 + Math.random() * 8}s linear infinite`,
              animationDelay: `${Math.random() * 5}s`
            }}
          />
        ))}
      </div>

      {/* Animated data streams */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        {Array.from({length: 6}).map((_, i) => (
          <div
            key={i}
            className="absolute text-green-400 font-mono text-xs opacity-30"
            style={{
              left: `${10 + i * 15}%`,
              animation: `data-stream ${6 + Math.random() * 4}s linear infinite`,
              animationDelay: `${Math.random() * 3}s`
            }}
          >
            {Array.from({length: 15}).map((_, j) => (
              <div key={j} className="mb-2">
                {Math.random() > 0.5 ? '1' : '0'}
              </div>
            ))}
          </div>
        ))}
      </div>

      <style jsx>{`
        @keyframes scan-vertical-1 {
          0% { top: -10px; opacity: 0.8; }
          50% { opacity: 1; }
          100% { top: 110%; opacity: 0; }
        }
        @keyframes scan-vertical-2 {
          0% { top: -5px; opacity: 0.5; }
          50% { opacity: 0.8; }
          100% { top: 105%; opacity: 0; }
        }
        @keyframes scan-horizontal-1 {
          0% { left: -10px; opacity: 0.6; }
          50% { opacity: 1; }
          100% { left: 110%; opacity: 0; }
        }
        @keyframes scan-horizontal-2 {
          0% { left: -5px; opacity: 0.4; }
          50% { opacity: 0.7; }
          100% { left: 105%; opacity: 0; }
        }
        @keyframes glow {
          0%, 100% { 
            text-shadow: 0 0 5px currentColor, 0 0 10px currentColor, 0 0 15px currentColor; 
            filter: brightness(1);
          }
          50% { 
            text-shadow: 0 0 10px currentColor, 0 0 20px currentColor, 0 0 30px currentColor, 0 0 40px currentColor; 
            filter: brightness(1.2);
          }
        }
        @keyframes float-particle-0 {
          0% { transform: translateY(100vh) translateX(0px); opacity: 0; }
          10% { opacity: 0.6; }
          90% { opacity: 0.6; }
          100% { transform: translateY(-10px) translateX(20px); opacity: 0; }
        }
        @keyframes float-particle-1 {
          0% { transform: translateY(100vh) translateX(0px); opacity: 0; }
          10% { opacity: 0.6; }
          90% { opacity: 0.6; }
          100% { transform: translateY(-10px) translateX(-20px); opacity: 0; }
        }
        @keyframes float-particle-2 {
          0% { transform: translateX(-10px) translateY(0px); opacity: 0; }
          10% { opacity: 0.6; }
          90% { opacity: 0.6; }
          100% { transform: translateX(100vw) translateY(10px); opacity: 0; }
        }
        @keyframes float-particle-3 {
          0% { transform: translateX(-10px) translateY(0px); opacity: 0; }
          10% { opacity: 0.6; }
          90% { opacity: 0.6; }
          100% { transform: translateX(100vw) translateY(-10px); opacity: 0; }
        }
        @keyframes data-stream {
          0% { transform: translateY(100vh); opacity: 0; }
          10% { opacity: 0.3; }
          90% { opacity: 0.3; }
          100% { transform: translateY(-100px); opacity: 0; }
        }
        .neon-text {
          animation: glow 2s ease-in-out infinite alternate;
        }
        @keyframes pulse-glow {
          0%, 100% { 
            box-shadow: 0 0 5px currentColor, 0 0 10px currentColor, 0 0 15px currentColor, inset 0 0 5px currentColor;
          }
          50% { 
            box-shadow: 0 0 10px currentColor, 0 0 20px currentColor, 0 0 30px currentColor, inset 0 0 10px currentColor;
          }
        }
      `}</style>
      
      {/* Main content */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}