/**
 * ISeeYou Dashboard Frontend Logic (Corrected & Extended)
 * This version includes full management for the Attack Modules tab.
 */

// --- STATE & CONFIG ---
let networkGraph = null;
const API_OPTIONS = (method = 'GET', body = null) => {
    const options = {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include' // IMPORTANT: Send cookies with every request
    };
    if (body) {
        options.body = JSON.stringify(body);
    }
    return options;
};

// --- API HELPER ---
async function apiFetch(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, options);
        if (response.status === 401) {
            showLogin(); 
            return null;
        }
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'API request failed' }));
            throw new Error(errorData.error);
        }
        return response.json();
    } catch (e) {
        console.error(`API fetch error for ${endpoint}:`, e);
        addLog(`ERROR: Network or API error - ${e.message}`, 'error');
        return null;
    }
}

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    checkSession();
});

async function checkSession() {
    const health = await apiFetch('/health');
    if (health && health.ok) {
        initializeDashboard();
    } else {
        showLogin();
    }
}

async function initializeDashboard() {
    document.getElementById('loginOverlay').style.display = 'none';
    document.getElementById('mainContent').style.display = 'block';

    // Set up standard UI event listeners
    document.getElementById('scanBtn').addEventListener('click', triggerScan);
    document.getElementById('filterInput').addEventListener('input', filterDevices);

    // Set up listeners for all attack module launch buttons
    document.querySelectorAll('.action-btn[data-module]').forEach(btn => {
        btn.addEventListener('click', handleAttackLaunch);
    });

    networkGraph = new NetworkGraph(document.getElementById('networkGraph'));
    initializeSSE();

    // Load initial device data
    loadDevices();

    addLog('Dashboard initialized and connected.', 'new');
}

// --- DEVICE MANAGEMENT ---
async function loadDevices() {
    try {
        const result = await apiFetch('/api/devices');
        if (result && result.devices) {
            updateDeviceList(result.devices);
            addLog(`Loaded ${result.devices.length} devices from server.`, 'new');
        }
    } catch (error) {
        addLog(`Failed to load devices: ${error.message}`, 'error');
    }
}

// --- AUTHENTICATION ---
async function handleLogin(event) {
    event.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const loginError = document.getElementById('loginError');
    loginError.textContent = '';

    const response = await fetch('/api/login', API_OPTIONS('POST', { username, password }));

    if (response.ok) {
        const result = await response.json();
        document.getElementById('currentUser').textContent = username;
        initializeDashboard();
    } else {
        const errorData = await response.json().catch(() => ({ error: 'Login failed' }));
        loginError.textContent = errorData.error || 'Invalid credentials. Please try again.';
    }
}

async function handleLogout() {
    await apiFetch('/logout', API_OPTIONS('POST'));
    showLogin();
}

function showLogin() {
    document.getElementById('loginOverlay').style.display = 'flex';
    document.getElementById('mainContent').style.display = 'none';
}

// --- REAL-TIME EVENTS (SSE) ---
function initializeSSE() {
    const eventSource = new EventSource('/events');

    eventSource.addEventListener('snapshot', event => {
        const devices = JSON.parse(event.data);
        updateDeviceList(devices);
        addLog(`Received initial snapshot of ${devices.length} devices.`, 'new');
    });

    eventSource.addEventListener('device_update', event => {
        const { device } = JSON.parse(event.data);
        updateDeviceInList(device);
    });

    eventSource.onerror = () => {
        addLog('SSE connection lost. Attempting to reconnect...', 'error');
        eventSource.close();
        setTimeout(initializeSSE, 5000);
    };
}

// --- DATA & UI UPDATES ---
function updateDeviceList(devices) {
    const deviceList = document.getElementById('deviceList');
    deviceList.innerHTML = '';

    if (!devices || devices.length === 0) {
        deviceList.innerHTML = `<div class="scan-status">No devices detected. Initiate a scan.</div>`;
        return;
    }
    
    devices.sort((a, b) => (b.last_seen || 0) - (a.last_seen || 0));

    devices.forEach(device => {
        const deviceItem = createDeviceElement(device);
        deviceList.appendChild(deviceItem);
    });

    networkGraph.update(devices);
}

function updateDeviceInList(device) {
    const deviceList = document.getElementById('deviceList');
    const deviceId = `device-${(device.mac || device.ip).replace(/[:.]/g, '-')}`;
    const existingEl = document.getElementById(deviceId);
    
    if (existingEl) {
        const updatedEl = createDeviceElement(device);
        existingEl.replaceWith(updatedEl);
    } else {
        const newEl = createDeviceElement(device);
        deviceList.prepend(newEl);
    }
    
    const allDevices = Array.from(deviceList.children).map(el => JSON.parse(el.dataset.device));
    networkGraph.update(allDevices);
}

function createDeviceElement(device) {
    const deviceItem = document.createElement('div');
    deviceItem.className = 'network-item';
    deviceItem.id = `device-${(device.mac || device.ip).replace(/[:.]/g, '-')}`;
    deviceItem.dataset.device = JSON.stringify(device);

    const status = device.source === 'active' ? 'online' : 'passive';
    const statusClass = status === 'online' ? 'status-up' : 'status-passive';

    deviceItem.innerHTML = `
        <div class="network-info">
            <div class="network-ssid">${device.hostname || device.ip}</div>
            <div class="network-details">
                IP: ${device.ip || 'N/A'} | MAC: ${device.mac || 'N/A'} | Status: <span class="${statusClass}">${status}</span>
            </div>
        </div>
        <div class="signal-strength">
            ${generateSignalBarsFromStatus(status)}
        </div>
    `;
    deviceItem.onclick = () => selectTarget(device);
    return deviceItem;
}

function addLog(message, type = "") {
    const logConsole = document.getElementById('logConsole');
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    logEntry.textContent = `[${timestamp}] ${message}`;
    logConsole.prepend(logEntry);
}

// --- UI INTERACTIONS ---
function switchTab(event, tabName) {
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    event.currentTarget.classList.add('active');
}

function selectTarget(device) {
    const intelSection = document.getElementById('targetIntelSection');
    intelSection.innerHTML = `
        <h3 class="section-title">DEVICE INTEL</h3>
        <div style="padding: 20px;">
            <div style="color: #00ccff; font-size: 1.2rem; margin-bottom: 10px;">🎯 ${device.hostname || device.ip}</div>
            <div style="color: #999; margin-bottom: 5px;">IP Address: ${device.ip || 'N/A'}</div>
            <div style="color: #999; margin-bottom: 5px;">MAC Address: ${device.mac || 'N/A'}</div>
            <div style="color: #999; margin-bottom: 5px;">Vendor: ${device.vendor || '...'}</div>
            <div style="color: #999; margin-bottom: 5px;">Open Ports: ${device.open_ports ? device.open_ports.join(', ') : 'N/A'}</div>
            <div style="color: #999;">Last Seen: ${new Date(device.last_seen * 1000).toLocaleString()}</div>
        </div>
    `;
    
    // Autofill attack module inputs
    document.querySelectorAll('input[data-autofill="mac"]').forEach(input => input.value = device.mac || '');
    document.querySelectorAll('input[data-autofill="channel"]').forEach(input => input.value = device.channel || '1');
    document.querySelectorAll('input[data-autofill="hostname"]').forEach(input => input.value = device.hostname || '');
    addLog(`Target ${device.mac || device.ip} selected. Attack modules are pre-filled.`, 'new');
}

async function triggerScan() {
    const scanBtn = document.getElementById('scanBtn');
    const scanStatusText = document.getElementById('scanStatusText');

    // Disable button and update UI
    scanBtn.disabled = true;
    scanBtn.textContent = 'SCANNING...';
    scanStatusText.textContent = 'Network scan in progress...';

    try {
        const result = await apiFetch('/api/scan', API_OPTIONS('POST'));

        if (result && result.started) {
            addLog('Network scan initiated successfully.', 'new');
            scanStatusText.textContent = 'Scan completed. Check device list for results.';
        } else {
            addLog('Failed to initiate network scan.', 'error');
            scanStatusText.textContent = 'Scan failed. Please try again.';
        }
    } catch (error) {
        addLog(`Scan error: ${error.message}`, 'error');
        scanStatusText.textContent = 'Scan failed due to network error.';
    } finally {
        // Re-enable button after a short delay
        setTimeout(() => {
            scanBtn.disabled = false;
            scanBtn.textContent = '▶ INITIATE SCAN';
        }, 2000);
    }
}

function filterDevices(e) {
    const filterText = e.target.value.toLowerCase();
    const deviceItems = document.querySelectorAll('.network-item');

    deviceItems.forEach(item => {
        const deviceData = JSON.parse(item.dataset.device || '{}');
        const searchableText = [
            deviceData.ip || '',
            deviceData.mac || '',
            deviceData.hostname || '',
            deviceData.vendor || ''
        ].join(' ').toLowerCase();

        if (searchableText.includes(filterText)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });

    // Update network graph with filtered devices
    const visibleDevices = Array.from(deviceItems)
        .filter(item => item.style.display !== 'none')
        .map(item => JSON.parse(item.dataset.device || '{}'));

    if (networkGraph) {
        networkGraph.update(visibleDevices);
    }
}

// --- ATTACK MODULE LOGIC ---
async function handleAttackLaunch(event) {
    const button = event.currentTarget;
    const moduleName = button.dataset.module;
    
    const payload = {};
    const moduleCard = button.closest('.module-card');
    const inputs = moduleCard.querySelectorAll('.module-input');
    
    let allInputsValid = true;
    inputs.forEach(input => {
        const key = input.id.split('-')[1];
        if (!input.value) {
            allInputsValid = false;
            input.style.borderColor = '#ff4444';
        } else {
            input.style.borderColor = '';
        }
        payload[key] = input.value;
    });

    if (!allInputsValid) {
        addLog(`ERROR: Missing required parameters for ${moduleName} module.`, 'error');
        return;
    }

    addLog(`Initiating ${moduleName} attack with parameters: ${JSON.stringify(payload)}`, 'warning');
    button.disabled = true;
    button.textContent = 'RUNNING...';

    const result = await apiFetch(`/api/attack/${moduleName}`, API_OPTIONS('POST', payload));

    if (result && result.status === 'ok') {
        addLog(`SUCCESS: ${moduleName} attack started with advanced optimizations`, 'new');
        if (result.optimizations_applied && result.optimizations_applied.length > 0) {
            addLog(`🚀 Applied optimizations: ${result.optimizations_applied.join(', ')}`, 'new');
        }
        if (result.attack_id) {
            addLog(`📊 Attack ID: ${result.attack_id} - Use analytics to monitor progress`, 'new');
        }
        if (result.recommendations && result.recommendations.length > 0) {
            addLog(`💡 Smart recommendations:`, 'new');
            result.recommendations.forEach(rec => addLog(`   • ${rec}`, 'new'));
        }
        addLog(`⚡ Attack running with PID: ${result.pid}`, 'new');
    } else {
        const errorMessage = result ? result.error : 'Unknown error.';
        addLog(`❌ Failed to start ${moduleName} attack. Reason: ${errorMessage}`, 'error');

        // Provide helpful troubleshooting tips
        if (errorMessage.includes('tools not found')) {
            addLog(`🔧 Install required tools: ${errorMessage.split(':')[1].trim()}`, 'warning');
        } else if (errorMessage.includes('interface')) {
            addLog(`📡 Check wireless interface availability and permissions`, 'warning');
        }
    }
    
    setTimeout(() => {
        button.disabled = false;
        button.textContent = 'LAUNCH';
    }, 5000);
}

// --- UTILITIES & VISUALS ---
function generateSignalBarsFromStatus(status) {
    const strength = status === 'online' ? 5 : 2;
    return Array.from({ length: 5 }, (_, i) => 
        `<div class="signal-bar ${i < strength ? 'active' : ''}" style="height: ${(i + 1) * 4}px;"></div>`
    ).join('');
}

class NetworkGraph {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.devices = [];
        this.animationId = null;
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());

        // Start animation loop
        this.animate();
    }

    resizeCanvas() {
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
    }

    update(devices) {
        this.devices = devices || [];
        this.draw();
    }

    draw() {
        const ctx = this.ctx;
        const width = this.canvas.width;
        const height = this.canvas.height;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Draw grid
        ctx.strokeStyle = 'rgba(0, 255, 0, 0.1)';
        ctx.lineWidth = 1;

        const gridSize = 20;
        for (let x = 0; x < width; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }
        for (let y = 0; y < height; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }

        if (this.devices.length === 0) {
            // Draw placeholder text
            ctx.fillStyle = 'rgba(0, 255, 0, 0.5)';
            ctx.font = '16px Courier New';
            ctx.textAlign = 'center';
            ctx.fillText('No devices detected', width / 2, height / 2);
            return;
        }

        // Draw connections between devices
        this.drawConnections();

        // Draw devices
        this.devices.forEach((device, index) => {
            this.drawDevice(device, index);
        });
    }

    drawConnections() {
        const ctx = this.ctx;
        ctx.strokeStyle = 'rgba(0, 255, 0, 0.3)';
        ctx.lineWidth = 2;

        for (let i = 0; i < this.devices.length; i++) {
            for (let j = i + 1; j < this.devices.length; j++) {
                const device1 = this.devices[i];
                const device2 = this.devices[j];

                // Draw connection if devices are on the same subnet
                if (this.areOnSameSubnet(device1.ip, device2.ip)) {
                    const pos1 = this.getDevicePosition(device1, i);
                    const pos2 = this.getDevicePosition(device2, j);

                    ctx.beginPath();
                    ctx.moveTo(pos1.x, pos1.y);
                    ctx.lineTo(pos2.x, pos2.y);
                    ctx.stroke();
                }
            }
        }
    }

    drawDevice(device, index) {
        const ctx = this.ctx;
        const pos = this.getDevicePosition(device, index);

        // Determine device color based on status
        const isOnline = device.source === 'active' || device.status === 'online';
        ctx.fillStyle = isOnline ? '#00ff00' : '#666666';
        ctx.strokeStyle = isOnline ? '#00cc00' : '#999999';
        ctx.lineWidth = 2;

        // Draw device circle
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 8, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();

        // Draw device label
        ctx.fillStyle = '#00ccff';
        ctx.font = '12px Courier New';
        ctx.textAlign = 'center';
        const label = device.hostname || device.ip || 'Unknown';
        ctx.fillText(label, pos.x, pos.y - 15);

        // Draw IP address
        ctx.fillStyle = '#999999';
        ctx.font = '10px Courier New';
        ctx.fillText(device.ip || '', pos.x, pos.y + 20);
    }

    getDevicePosition(device, index) {
        const width = this.canvas.width;
        const height = this.canvas.height;

        // Create a deterministic but distributed layout
        const hash = this.simpleHash(device.ip || device.mac || index.toString());
        const x = (hash % 1000) / 1000 * (width - 100) + 50;
        const y = (this.simpleHash(device.ip || device.mac || (index + 1).toString()) % 1000) / 1000 * (height - 100) + 50;

        return { x, y };
    }

    simpleHash(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return Math.abs(hash);
    }

    areOnSameSubnet(ip1, ip2) {
        if (!ip1 || !ip2) return false;

        try {
            const [a1, b1, c1] = ip1.split('.').map(Number);
            const [a2, b2, c2] = ip2.split('.').map(Number);

            // Consider devices on the same /24 subnet as connected
            return a1 === a2 && b1 === b2;
        } catch {
            return false;
        }
    }

    animate() {
        this.draw();
        this.animationId = requestAnimationFrame(() => this.animate());
    }

    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }
}