// MinePyt Debug Server - Map Visualization

const socket = io();

// Canvas setup
const canvas = document.getElementById('map-canvas');
const ctx = canvas.getContext('2d');

// State
let mapData = {
    botPosition: { x: 0, y: 64, z: 0 },
    threats: [],
    interests: [],
    players: [],
    terrain: {}
};

let zoom = 1.0;
let offsetX = 0;
let offsetZ = 0;
let showGrid = true;
let selectedLayer = 'all';

// Colors
const COLORS = {
    bot: '#4CAF50',
    threat: '#f44336',
    interest: '#4CAF50',
    player: '#2196F3',
    hazard: '#ff9800'
};

// Socket Events
socket.on('connect', () => {
    console.log('Connected to debug server');
    requestMapData();
});

socket.on('initial_state', (state) => {
    if (state.position) {
        mapData.botPosition = state.position;
    }
    if (state.sensors) {
        mapData.threats = state.sensors.threats || [];
        mapData.interests = state.sensors.interests || [];
        mapData.players = state.sensors.players || [];
    }
    drawMap();
});

socket.on('position_update', (data) => {
    mapData.botPosition = data.data;
    drawMap();
});

socket.on('sensors_update', (data) => {
    mapData.threats = data.data.threats || [];
    mapData.interests = data.data.interests || [];
    mapData.players = data.data.players || [];
    drawMap();
});

// Request map data
function requestMapData() {
    socket.emit('request_state');
}

// Convert world coordinates to canvas coordinates
function worldToCanvas(x, z) {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    
    const canvasX = centerX + (x - mapData.botPosition.x + offsetX) * 10 * zoom;
    const canvasY = centerY + (z - mapData.botPosition.z + offsetZ) * 10 * zoom;
    
    return { x: canvasX, y: canvasY };
}

// Draw map
function drawMap() {
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw grid
    if (showGrid) {
        drawGrid();
    }
    
    // Draw terrain (hazards)
    if (selectedLayer === 'all' || selectedLayer === 'terrain') {
        drawTerrain();
    }
    
    // Draw interests
    if (selectedLayer === 'all' || selectedLayer === 'interests') {
        drawInterests();
    }
    
    // Draw threats
    if (selectedLayer === 'all' || selectedLayer === 'threats') {
        drawThreats();
    }
    
    // Draw players
    if (selectedLayer === 'all') {
        drawPlayers();
    }
    
    // Draw bot in center
    drawBot();
    
    // Update info display
    updateInfo();
}

function drawGrid() {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    
    // Vertical lines
    for (let i = -20; i <= 20; i++) {
        const x = centerX + i * 10 * zoom;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
    }
    
    // Horizontal lines
    for (let i = -20; i <= 20; i++) {
        const y = centerY + i * 10 * zoom;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
    }
}

function drawBot() {
    const center = worldToCanvas(mapData.botPosition.x, mapData.botPosition.z);
    
    // Draw bot circle
    ctx.beginPath();
    ctx.arc(center.x, center.y, 8 * zoom, 0, Math.PI * 2);
    ctx.fillStyle = COLORS.bot;
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // Draw direction indicator
    const yaw = mapData.botPosition.yaw || 0;
    const yawRad = (yaw * Math.PI) / 180;
    
    ctx.beginPath();
    ctx.moveTo(center.x, center.y);
    ctx.lineTo(
        center.x + Math.sin(yawRad) * 20 * zoom,
        center.y - Math.cos(yawRad) * 20 * zoom
    );
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.stroke();
}

function drawThreats() {
    mapData.threats.forEach(threat => {
        if (!threat.position) return;
        
        const pos = worldToCanvas(threat.position.x, threat.position.z);
        
        // Draw threat
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 6 * zoom, 0, Math.PI * 2);
        ctx.fillStyle = COLORS.threat;
        ctx.fill();
        
        // Draw label
        ctx.fillStyle = '#fff';
        ctx.font = '10px Arial';
        ctx.fillText(threat.type || '?', pos.x + 10, pos.y);
    });
}

function drawInterests() {
    mapData.interests.forEach(interest => {
        if (!interest.position) return;
        
        const pos = worldToCanvas(interest.position.x, interest.position.z);
        
        // Draw interest
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 5 * zoom, 0, Math.PI * 2);
        ctx.fillStyle = COLORS.interest;
        ctx.fill();
        
        // Draw label
        ctx.fillStyle = '#fff';
        ctx.font = '10px Arial';
        ctx.fillText(interest.type || '?', pos.x + 8, pos.y);
    });
}

function drawPlayers() {
    mapData.players.forEach(player => {
        if (!player.position) return;
        
        const pos = worldToCanvas(player.position.x, player.position.z);
        
        // Draw player
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 7 * zoom, 0, Math.PI * 2);
        ctx.fillStyle = COLORS.player;
        ctx.fill();
        
        // Draw label
        ctx.fillStyle = '#fff';
        ctx.font = '10px Arial';
        ctx.fillText(player.name || 'Player', pos.x + 10, pos.y);
    });
}

function drawTerrain() {
    const terrain = mapData.terrain || {};
    
    Object.values(terrain).forEach(tile => {
        if (!tile.hazard || !tile.position) return;
        
        const pos = worldToCanvas(tile.position.x, tile.position.z);
        
        // Draw hazard
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 4 * zoom, 0, Math.PI * 2);
        ctx.fillStyle = COLORS.hazard;
        ctx.fill();
    });
}

function updateInfo() {
    const pos = mapData.botPosition;
    document.getElementById('bot-pos').textContent = 
        `X: ${pos.x.toFixed(1)}, Y: ${pos.y.toFixed(1)}, Z: ${pos.z.toFixed(1)}`;
    document.getElementById('zoom-level').textContent = `${zoom.toFixed(1)}x`;
}

// Event listeners
document.getElementById('zoom-in')?.addEventListener('click', () => {
    zoom = Math.min(zoom * 1.2, 5);
    drawMap();
});

document.getElementById('zoom-out')?.addEventListener('click', () => {
    zoom = Math.max(zoom / 1.2, 0.2);
    drawMap();
});

document.getElementById('center-bot')?.addEventListener('click', () => {
    offsetX = 0;
    offsetZ = 0;
    drawMap();
});

document.getElementById('toggle-grid')?.addEventListener('click', () => {
    showGrid = !showGrid;
    drawMap();
});

document.getElementById('layer-select')?.addEventListener('change', (e) => {
    selectedLayer = e.target.value;
    drawMap();
});

// Mouse drag to pan
let isDragging = false;
let lastMouseX, lastMouseY;

canvas.addEventListener('mousedown', (e) => {
    isDragging = true;
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
});

canvas.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    
    const dx = e.clientX - lastMouseX;
    const dy = e.clientY - lastMouseY;
    
    offsetX -= dx / (10 * zoom);
    offsetZ -= dy / (10 * zoom);
    
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
    
    drawMap();
});

canvas.addEventListener('mouseup', () => {
    isDragging = false;
});

canvas.addEventListener('mouseleave', () => {
    isDragging = false;
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Map visualization initialized');
    drawMap();
    
    // Request data every 2 seconds
    setInterval(requestMapData, 2000);
});
