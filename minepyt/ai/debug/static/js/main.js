// MinePyt Debug Server - Main JavaScript

const socket = io();

// State
let currentState = {};
let events = [];

// DOM Elements
const positionEl = document.getElementById('position');
const healthBarEl = document.getElementById('health-bar');
const healthTextEl = document.getElementById('health-text');
const hungerBarEl = document.getElementById('hunger-bar');
const hungerTextEl = document.getElementById('hunger-text');
const taskEl = document.getElementById('task');
const tickTimeEl = document.getElementById('tick-time');
const memoryUsageEl = document.getElementById('memory-usage');
const layer4VectorEl = document.getElementById('layer4-vector');
const layer3VectorEl = document.getElementById('layer3-vector');
const layer2VectorEl = document.getElementById('layer2-vector');
const layer1VectorEl = document.getElementById('layer1-vector');
const finalVectorEl = document.getElementById('final-vector');
const eventsListEl = document.getElementById('events-list');

// Socket Events
socket.on('connect', () => {
    console.log('Connected to debug server');
    requestState();
});

socket.on('disconnect', () => {
    console.log('Disconnected from debug server');
});

socket.on('initial_state', (state) => {
    console.log('Received initial state');
    currentState = state;
    updateDashboard();
});

socket.on('position_update', (data) => {
    currentState.position = data.data;
    updatePosition();
});

socket.on('health_update', (data) => {
    currentState.health = data.data;
    updateHealth();
});

socket.on('layers_update', (data) => {
    currentState.layers = data.data;
    updateLayers();
});

socket.on('event', (data) => {
    addEvent(data);
});

// Request current state
function requestState() {
    socket.emit('request_state');
}

// Update functions
function updateDashboard() {
    updatePosition();
    updateHealth();
    updateTask();
    updatePerformance();
    updateLayers();
}

function updatePosition() {
    if (!currentState.position) return;
    
    const pos = currentState.position;
    positionEl.innerHTML = `
        <div>X: ${pos.x.toFixed(2)}</div>
        <div>Y: ${pos.y.toFixed(2)}</div>
        <div>Z: ${pos.z.toFixed(2)}</div>
    `;
}

function updateHealth() {
    if (!currentState.health) return;
    
    const health = currentState.health;
    
    // Health bar
    const healthPercent = health.health_percent || 100;
    healthBarEl.style.width = `${healthPercent}%`;
    healthTextEl.textContent = `${health.health.toFixed(1)}/${health.max_health}`;
    
    // Hunger bar
    const hungerPercent = health.food_percent || 100;
    hungerBarEl.style.width = `${hungerPercent}%`;
    hungerTextEl.textContent = `${health.food}/${health.max_food}`;
}

function updateTask() {
    if (!currentState.task) return;
    
    const task = currentState.task;
    taskEl.innerHTML = `
        <span class="task-name">${task.name || 'Idle'}</span>
        <span class="task-status">${task.status || 'No active task'}</span>
    `;
}

function updatePerformance() {
    if (!currentState.performance) return;
    
    const perf = currentState.performance;
    tickTimeEl.textContent = `${perf.avg_tick_time_ms?.toFixed(2) || '0.00'} ms`;
}

function updateLayers() {
    if (!currentState.layers) return;
    
    const layers = currentState.layers;
    
    // Layer 4 - Goal
    if (layers.layer4_goal) {
        const v = layers.layer4_goal;
        layer4VectorEl.textContent = `(${v.dx?.toFixed(2)}, ${v.dy?.toFixed(2)}, ${v.dz?.toFixed(2)})`;
    }
    
    // Layer 3 - Tactical
    if (layers.layer3_tactical && layers.layer3_tactical.length > 0) {
        layer3VectorEl.textContent = `${layers.layer3_tactical.length} vectors`;
    }
    
    // Layer 2 - Avoid
    if (layers.layer2_avoid && layers.layer2_avoid.length > 0) {
        layer2VectorEl.textContent = `${layers.layer2_avoid.length} vectors`;
    }
    
    // Layer 1 - Physics
    if (layers.layer1_physics) {
        const v = layers.layer1_physics;
        layer1VectorEl.textContent = `(${v.dx?.toFixed(2)}, ${v.dy?.toFixed(2)}, ${v.dz?.toFixed(2)})`;
    }
    
    // Final vector
    if (layers.final_vector) {
        const v = layers.final_vector;
        finalVectorEl.textContent = `(${v.dx?.toFixed(2)}, ${v.dy?.toFixed(2)}, ${v.dz?.toFixed(2)})`;
    }
}

function addEvent(event) {
    events.unshift(event);
    if (events.length > 50) {
        events.pop();
    }
    updateEventsList();
}

function updateEventsList() {
    if (events.length === 0) {
        eventsListEl.innerHTML = '<span class="loading">No events yet</span>';
        return;
    }
    
    eventsListEl.innerHTML = events.slice(0, 10).map(event => {
        const time = new Date(event.timestamp * 1000).toLocaleTimeString();
        const typeClass = event.event_type?.includes('error') ? 'error' : 
                         event.event_type?.includes('warning') ? 'warning' : 'info';
        
        return `
            <div class="event-item">
                <span class="event-time">${time}</span>
                <span class="event-type ${typeClass}">${event.event_type}</span>
            </div>
        `;
    }).join('');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard initialized');
    
    // Request state every 5 seconds
    setInterval(requestState, 5000);
});
