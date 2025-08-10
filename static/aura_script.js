

function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
}
window.addEventListener('load', ()=>{ /* initialize login overlay when needed */ });
/**
 * Aura Dashboard Frontend Logic
 * Connects the UI to the live backend API endpoints for network monitoring.
 */

// --- STATE & CONFIG ---
let AUTH_TOKEN = null; // Will be fetched or prompted
const API_HEADERS = () => ({
    'Authorization': `Bearer ${AUTH_TOKEN}`,
    'Content-Type': 'application/json'
});

// --- API HELPER ---
async function apiFetch(endpoint, options = {}) {
    const response = await fetch(endpoint, { ...options,  });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'API request failed');
    }
    return response.json();
}

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', async () => {
    AUTH_TOKEN = prompt("Enter your dashboard auth token:");
    if (!AUTH_TOKEN) {
        alert("Authentication token is required to use the dashboard.");
        return;
    }
    
    initializeDashboard();
    startGraphAnimation();
    setInterval(updateData, 5000); // Refresh data every 5 seconds
});

async function initializeDashboard() {
    try {
        const config = await apiFetch('/api/config');
        document.getElementById('interfaceName').textContent = config.interface;
        updateData();
    } catch (error) {
        console.error("Initialization failed:", error);
        addLog(`ERROR: Failed to initialize dashboard - ${error.message}`, 'error');
    }
}

// --- DATA UPDATES ---
async function updateData() {
    try {
        const devices = await apiFetch('/api/devices');
        updateDeviceList(devices);
        const logs = await apiFetch('/api/logs');
        updateLogConsole(logs);
    } catch (error) {
        console.error("Data update failed:", error);
        addLog(`ERROR: Failed to fetch data - ${error.message}`, 'error');
    }
}

function updateDeviceList(devices) {
    const deviceList = document.getElementById('deviceList');
    clearChildren(deviceList); // Clear old entries safely

    if (Object.keys(devices).length === 0) {
        deviceList.innerHTML = `<div class="scan-status">No devices detected. Initiate a scan.</div>`;
        return;
    }

    Object.entries(devices).forEach(([ip, data]) => {
        const deviceItem = document.createElement('div');
        deviceItem.className = 'network-item';
        // Renaming to match backend data: ssid->ip, bssid->mac, encryption->status
        deviceItem.innerHTML = `
            <div class="network-info">
                <div class="network-ssid">${ip} (${data.hostname || 'N/A'})</div>
                <div class="network-details">
                    MAC: ${data.mac || 'N/A'} | Status: <span class="${data.status === 'up' ? 'status-up' : ''}">${data.status || 'passive'}</span> | Vendor: ${data.vendor || '...'}
                </div>
            </div>
            <div class="signal-strength">
                ${generateSignalBarsFromStatus(data.status)}
            </div>
        `;
        deviceItem.onclick = () => selectTarget(ip, data);
        deviceList.appendChild(deviceItem);
    });
}

function updateLogConsole(logs) {
    const logConsole = document.getElementById('logConsole');
    clearChildren(logConsole); // Clear old logs safely
    logs.forEach(logLine => {
        let type = '';
        if (logLine.includes('WARNING')) type = 'warning';
        if (logLine.includes('ERROR') || logLine.includes('CRITICAL')) type = 'error';
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        logEntry.textContent = logLine.trim();
        logConsole.appendChild(logEntry);
    });
    logConsole.scrollTop = logConsole.scrollHeight;
}

// --- UI INTERACTIONS ---
function switchTab(event, tabName) {
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    event.currentTarget.classList.add('active');
}

function selectTarget(ip, data) {
    const intelSection = document.getElementById('targetIntelSection');
    clearChildren(intelSection); intelSection.appendChild(el('h3','DEVICE INTEL','section-title')); intelSection.appendChild(document.createElement('div')); // placeholder; populate next
        <h3 class="section-title">DEVICE INTEL</h3>
        <div style="padding: 20px;">
            <div style="color: #00ccff; font-size: 1.2rem; margin-bottom: 10px;">🎯 ${ip}</div>
            <div style="color: #999; margin-bottom: 5px;">Hostname: ${data.hostname || 'N/A'}</div>
            <div style="color: #999; margin-bottom: 5px;">MAC Address: ${data.mac || 'N/A'}</div>
            <div style="color: #999; margin-bottom: 5px;">Vendor: ${data.vendor || '...'}</div>
            <div style="color: #999;">Last Seen: ${new Date(data.last_seen * 1000).toLocaleString()}</div>
        </div>
    `;
    addLog(`Target selected: ${ip}`, 'new');
}

document.getElementById('scanBtn').addEventListener('click', async () => {
    const btn = document.getElementById('scanBtn');
    const statusText = document.getElementById('scanStatusText');
    const indicator = document.getElementById('scanStatusIndicator');

    btn.disabled = true;
    btn.textContent = "SCANNING...";
    statusText.textContent = "Active probe initiated across the subnet...";
    indicator.className = "status-indicator scanning";
    addLog("On-demand scan initiated via UI.", 'new');

    try {
        await fetch('/api/scan/start', { method: 'POST', credentials: 'include' });
    } catch (error) {
        addLog(`ERROR: Could not start scan - ${error.message}`, 'error');
    }

    setTimeout(() => {
        btn.disabled = false;
        btn.textContent = "▶ INITIATE SCAN";
        statusText.textContent = "Scan command sent. Check logs for progress.";
        indicator.className = "status-indicator online";
    }, 3000); // Re-enable button after 3 seconds
});

document.getElementById('filterInput').addEventListener('input', (e) => {
    const filter = e.target.value.toLowerCase();
    document.querySelectorAll('.network-item').forEach(item => {
        item.style.display = item.textContent.toLowerCase().includes(filter) ? 'flex' : 'none';
    });
});

// --- UTILITIES & VISUALS ---
function addLog(message, type = "") {
    const logConsole = document.getElementById('logConsole');
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    logEntry.textContent = `[${timestamp}] ${message}`;
    logConsole.appendChild(logEntry);
    logConsole.scrollTop = logConsole.scrollHeight;
}

function generateSignalBarsFromStatus(status) {
    const strength = status === 'up' ? 5 : 2; // Simple representation
    let bars = '';
    for (let i = 0; i < 5; i++) {
        const height = (i + 1) * 4;
        const active = i < strength ? 'active' : '';
        bars += `<div class="signal-bar ${active}" style="height: ${height}px;"></div>`;
    }
    return bars;
}

// Graph animation (cosmetic, as in original HTML)
function startGraphAnimation() {
    const canvas = document.getElementById('networkGraph');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    let nodes = [], connections = [], frame = 0;

    const centerX = canvas.width / 2, centerY = canvas.height / 2;
    nodes.push({ x: centerX, y: centerY, radius: 8, color: '#ff6b6b' }); // Central node
    for (let i = 0; i < 7; i++) {
        const angle = (i / 7) * Math.PI * 2;
        const dist = 60 + Math.random() * 50;
        nodes.push({ x: centerX + Math.cos(angle) * dist, y: centerY + Math.sin(angle) * dist, radius: 4, color: '#00ccff' });
        connections.push({ from: 0, to: i + 1, strength: 0.3 + Math.random() * 0.7 });
    }

    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        connections.forEach(c => {
            ctx.beginPath();
            ctx.moveTo(nodes[c.from].x, nodes[c.from].y);
            ctx.lineTo(nodes[c.to].x, nodes[c.to].y);
            ctx.strokeStyle = `rgba(0, 255, 0, ${c.strength * 0.5})`;
            ctx.stroke();
        });
        nodes.forEach((n, i) => {
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
            ctx.fillStyle = n.color;
            ctx.fill();
            if (i === 0) { // Pulse effect for central node
                ctx.beginPath();
                ctx.arc(n.x, n.y, n.radius + Math.sin(frame * 0.05) * 3, 0, Math.PI * 2);
                ctx.strokeStyle = `rgba(255, 107, 107, ${0.3 + Math.sin(frame * 0.05) * 0.2})`;
                ctx.stroke();
            }
        });
        frame++;
        requestAnimationFrame(draw);
    }
    draw();
}