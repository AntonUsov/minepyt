// MinePyt Debug Server - Sensors Visualization

const socket = io();

// State
let sensorsData = {
    threats: [],
    interests: [],
    terrain: {},
    players: []
};

// DOM Elements
const threatsBody = document.getElementById('threats-body');
const interestsBody = document.getElementById('interests-body');
const terrainBody = document.getElementById('terrain-body');
const playersBody = document.getElementById('players-body');
const totalThreats = document.getElementById('total-threats');
const totalInterests = document.getElementById('total-interests');
const scanRange = document.getElementById('scan-range');

// Socket Events
socket.on('connect', () => {
    console.log('Connected to debug server');
    requestSensors();
});

socket.on('initial_state', (state) => {
    if (state.sensors) {
        sensorsData = state.sensors;
        updateSensorsDisplay();
    }
});

socket.on('sensors_update', (data) => {
    sensorsData = data.data;
    updateSensorsDisplay();
});

socket.on('sensors_data', (sensors) => {
    sensorsData = sensors;
    updateSensorsDisplay();
});

// Request sensors data
function requestSensors() {
    socket.emit('request_sensors');
}

// Update display
function updateSensorsDisplay() {
    updateThreats();
    updateInterests();
    updateTerrain();
    updatePlayers();
    updateStats();
}

function updateThreats() {
    const threats = sensorsData.threats || [];
    
    if (threats.length === 0) {
        threatsBody.innerHTML = '<span class="no-data">No threats detected</span>';
    } else {
        threatsBody.innerHTML = threats.map(threat => `
            <div class="threat-item">
                <div class="threat-name">${threat.type || 'Unknown'}</div>
                <div class="threat-distance">${threat.distance?.toFixed(1) || '?'} blocks away</div>
                <div class="threat-danger">Danger: ${((threat.danger_level || 0) * 100).toFixed(0)}%</div>
            </div>
        `).join('');
    }
}

function updateInterests() {
    const interests = sensorsData.interests || [];
    
    if (interests.length === 0) {
        interestsBody.innerHTML = '<span class="no-data">No interests detected</span>';
    } else {
        interestsBody.innerHTML = interests.map(interest => `
            <div class="interest-item">
                <div class="interest-name">${interest.type || 'Unknown'}</div>
                <div class="interest-distance">${interest.distance?.toFixed(1) || '?'} blocks away</div>
                <div class="interest-priority">Priority: ${((interest.priority || 1) * 100).toFixed(0)}%</div>
            </div>
        `).join('');
    }
}

function updateTerrain() {
    const terrain = sensorsData.terrain || {};
    
    if (Object.keys(terrain).length === 0) {
        terrainBody.innerHTML = '<span class="no-data">No terrain data</span>';
    } else {
        const hazards = [];
        for (const [key, data] of Object.entries(terrain)) {
            if (data.hazard) {
                hazards.push(data);
            }
        }
        
        if (hazards.length === 0) {
            terrainBody.innerHTML = '<span class="no-data">No hazards detected</span>';
        } else {
            terrainBody.innerHTML = hazards.map(hazard => `
                <div class="terrain-item hazard">
                    <div class="hazard-type">${hazard.type || 'Hazard'}</div>
                    <div class="hazard-distance">${hazard.distance?.toFixed(1) || '?'} blocks</div>
                </div>
            `).join('');
        }
    }
}

function updatePlayers() {
    const players = sensorsData.players || [];
    
    if (players.length === 0) {
        playersBody.innerHTML = '<span class="no-data">No players nearby</span>';
    } else {
        playersBody.innerHTML = players.map(player => `
            <div class="player-item">
                <div class="player-name">${player.name || 'Unknown'}</div>
                <div class="player-distance">${player.distance?.toFixed(1) || '?'} blocks away</div>
            </div>
        `).join('');
    }
}

function updateStats() {
    const threats = sensorsData.threats || [];
    const interests = sensorsData.interests || [];
    
    totalThreats.textContent = threats.length;
    totalInterests.textContent = interests.length;
    scanRange.textContent = '16 blocks'; // Default scan range
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Sensors visualization initialized');
    
    // Request sensors every 2 seconds
    setInterval(requestSensors, 2000);
});
