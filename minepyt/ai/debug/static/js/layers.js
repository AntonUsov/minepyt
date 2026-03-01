// MinePyt Debug Server - Layers Visualization

const socket = io();

// Canvas setup
const canvas = document.getElementById('vector-canvas');
const ctx = canvas.getContext('2d');

// State
let layersData = {};
let showGrid = true;
let scale = 100;

// Colors for each layer
const COLORS = {
    goal: '#00ff00',
    tactical: '#ffff00',
    avoid: '#ff0000',
    physics: '#00ffff',
    final: '#ffffff'
};

// Socket Events
socket.on('connect', () => {
    console.log('Connected to debug server');
    requestLayers();
});

socket.on('initial_state', (state) => {
    if (state.layers) {
        layersData = state.layers;
        updateLayersDisplay();
        drawVectors();
    }
});

socket.on('layers_update', (data) => {
    layersData = data.data;
    updateLayersDisplay();
    drawVectors();
});

socket.on('layers_state', (layers) => {
    layersData = layers;
    updateLayersDisplay();
    drawVectors();
});

// Request layers data
function requestLayers() {
    socket.emit('request_layers');
}

// Update DOM elements
function updateLayersDisplay() {
    // Layer 4 - Goal
    if (layersData.layer4_goal) {
        const v = layersData.layer4_goal;
        document.getElementById('goal-x').textContent = v.dx?.toFixed(3) || '0.000';
        document.getElementById('goal-y').textContent = v.dy?.toFixed(3) || '0.000';
        document.getElementById('goal-z').textContent = v.dz?.toFixed(3) || '0.000';
        document.getElementById('goal-info').textContent = v.info || 'Moving';
    }
    
    // Layer 3 - Tactical
    const tacticalList = document.getElementById('tactical-vectors');
    if (layersData.layer3_tactical && layersData.layer3_tactical.length > 0) {
        tacticalList.innerHTML = layersData.layer3_tactical.map(v => `
            <div class="vector-item">
                <span class="vector-name">${v.name || 'Tactical'}</span>
                <span class="vector-coords">(${v.dx?.toFixed(2)}, ${v.dy?.toFixed(2)}, ${v.dz?.toFixed(2)})</span>
                <span class="vector-priority">Priority: ${v.priority || 0.5}</span>
            </div>
        `).join('');
    } else {
        tacticalList.innerHTML = '<span class="no-data">No tactical vectors</span>';
    }
    
    // Layer 2 - Avoid
    const avoidList = document.getElementById('avoid-vectors');
    if (layersData.layer2_avoid && layersData.layer2_avoid.length > 0) {
        avoidList.innerHTML = layersData.layer2_avoid.map(v => `
            <div class="vector-item">
                <span class="vector-name">${v.name || 'Avoid'}</span>
                <span class="vector-coords">(${v.dx?.toFixed(2)}, ${v.dy?.toFixed(2)}, ${v.dz?.toFixed(2)})</span>
                <span class="vector-danger">Danger: ${v.danger || 0.5}</span>
            </div>
        `).join('');
    } else {
        avoidList.innerHTML = '<span class="no-data">No avoid vectors</span>';
    }
    
    // Layer 1 - Physics
    if (layersData.layer1_physics) {
        const v = layersData.layer1_physics;
        document.getElementById('physics-x').textContent = v.dx?.toFixed(3) || '0.000';
        document.getElementById('physics-y').textContent = v.dy?.toFixed(3) || '0.000';
        document.getElementById('physics-z').textContent = v.dz?.toFixed(3) || '0.000';
        document.getElementById('physics-info').textContent = `Valid directions: ${v.valid_directions || 8}`;
    }
    
    // Final Vector
    if (layersData.final_vector) {
        const v = layersData.final_vector;
        document.getElementById('final-x').textContent = v.dx?.toFixed(3) || '0.000';
        document.getElementById('final-y').textContent = v.dy?.toFixed(3) || '0.000';
        document.getElementById('final-z').textContent = v.dz?.toFixed(3) || '0.000';
        document.getElementById('final-info').textContent = v.info || 'Moving';
    }
}

// Draw vectors on canvas
function drawVectors() {
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    
    // Draw grid
    if (showGrid) {
        drawGrid(centerX, centerY);
    }
    
    // Draw bot in center
    ctx.beginPath();
    ctx.arc(centerX, centerY, 10, 0, Math.PI * 2);
    ctx.fillStyle = '#4CAF50';
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // Draw Layer 4 - Goal
    if (layersData.layer4_goal) {
        drawArrow(centerX, centerY, layersData.layer4_goal, COLORS.goal, 'GOAL', 2);
    }
    
    // Draw Layer 3 - Tactical
    if (layersData.layer3_tactical) {
        layersData.layer3_tactical.forEach(v => {
            drawArrow(centerX, centerY, v, COLORS.tactical, v.name || 'TACT', 1.5);
        });
    }
    
    // Draw Layer 2 - Avoid
    if (layersData.layer2_avoid) {
        layersData.layer2_avoid.forEach(v => {
            drawArrow(centerX, centerY, v, COLORS.avoid, v.name || 'AVOID', 1.5);
        });
    }
    
    // Draw Layer 1 - Physics
    if (layersData.layer1_physics) {
        drawArrow(centerX, centerY, layersData.layer1_physics, COLORS.physics, 'PHYS', 1);
    }
    
    // Draw Final Vector (thickest)
    if (layersData.final_vector) {
        drawArrow(centerX, centerY, layersData.final_vector, COLORS.final, 'FINAL', 3);
    }
}

// Draw grid
function drawGrid(cx, cy) {
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    
    // Vertical lines
    for (let x = 0; x < canvas.width; x += 50) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
    }
    
    // Horizontal lines
    for (let y = 0; y < canvas.height; y += 50) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
    }
    
    // Center lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.beginPath();
    ctx.moveTo(cx, 0);
    ctx.lineTo(cx, canvas.height);
    ctx.stroke();
    
    ctx.beginPath();
    ctx.moveTo(0, cy);
    ctx.lineTo(canvas.width, cy);
    ctx.stroke();
}

// Draw arrow
function drawArrow(cx, cy, vector, color, label, width = 2) {
    if (!vector || (vector.dx === 0 && vector.dz === 0)) return;
    
    const endX = cx + vector.dx * scale;
    const endY = cy - vector.dz * scale; // Invert Z for screen coordinates
    
    // Draw line
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.moveTo(cx, cy);
    ctx.lineTo(endX, endY);
    ctx.stroke();
    
    // Draw arrowhead
    const angle = Math.atan2(endY - cy, endX - cx);
    const arrowLength = 10;
    
    ctx.beginPath();
    ctx.moveTo(endX, endY);
    ctx.lineTo(
        endX - arrowLength * Math.cos(angle - Math.PI / 6),
        endY - arrowLength * Math.sin(angle - Math.PI / 6)
    );
    ctx.moveTo(endX, endY);
    ctx.lineTo(
        endX - arrowLength * Math.cos(angle + Math.PI / 6),
        endY - arrowLength * Math.sin(angle + Math.PI / 6)
    );
    ctx.stroke();
    
    // Draw label
    ctx.fillStyle = color;
    ctx.font = '12px Arial';
    ctx.fillText(label, endX + 5, endY - 5);
}

// Event listeners
document.getElementById('clear-canvas')?.addEventListener('click', () => {
    layersData = {};
    drawVectors();
});

document.getElementById('toggle-grid')?.addEventListener('click', () => {
    showGrid = !showGrid;
    drawVectors();
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Layers visualization initialized');
    drawVectors();
    
    // Request layers every 2 seconds
    setInterval(requestLayers, 2000);
});
