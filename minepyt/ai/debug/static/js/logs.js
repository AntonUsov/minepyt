// MinePyt Debug Server - Logs Visualization

const socket = io();

// State
let logs = [];
let currentFilter = 'all';
const MAX_LOGS = 100;

// DOM Elements
const logList = document.getElementById('log-list');
const logTotal = document.getElementById('log-total');
const logInfoCount = document.getElementById('log-info-count');
const logWarningCount = document.getElementById('log-warning-count');
const logErrorCount = document.getElementById('log-error-count');

// Socket Events
socket.on('connect', () => {
    console.log('Connected to debug server');
    fetchLogs();
});

socket.on('log', (data) => {
    addLog(data);
});

socket.on('initial_state', (state) => {
    if (state.logs) {
        logs = state.logs.slice(-MAX_LOGS);
    }
    updateDisplay();
});

// Fetch logs from server
async function fetchLogs() {
    try {
        const response = await fetch('/api/logs?limit=50');
        const data = await response.json();
        logs = data.logs || [];
        updateDisplay();
    } catch (error) {
        console.error('Error fetching logs:', error);
    }
}

// Add log
function addLog(logEntry) {
    logs.unshift(logEntry);
    if (logs.length > MAX_LOGS) {
        logs.pop();
    }
    updateDisplay();
}

// Filter logs
function filterLogs(level) {
    currentFilter = level;
    
    // Update active button
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.onclick.toString().includes(level)) {
            btn.classList.add('active');
        }
    });
    
    updateDisplay();
}

// Update display
function updateDisplay() {
    let filteredLogs = logs;
    
    if (currentFilter !== 'all') {
        filteredLogs = logs.filter(log => log.level === currentFilter);
    }
    
    // Render logs
    if (filteredLogs.length === 0) {
        logList.innerHTML = '<span class="no-data">No logs yet</span>';
        return;
    }
    
    logList.innerHTML = filteredLogs.map(log => {
        const time = new Date(log.timestamp * 1000).toLocaleTimeString();
        const levelClass = log.level || 'info';
        
        return `
            <div class="log-item">
                <span class="log-time">${time}</span>
                <span class="log-level ${levelClass}">${log.level || 'info'}</span>
                <span class="log-message">${log.message || log.type || 'Event'}</span>
            </div>
        `;
    }).join('');
    
    // Update stats
    logTotal.textContent = logs.length;
    logInfoCount.textContent = logs.filter(l => l.level === 'info').length;
    logWarningCount.textContent = logs.filter(l => l.level === 'warning').length;
    logErrorCount.textContent = logs.filter(l => l.level === 'error').length;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Logs visualization initialized');
    
    // Fetch logs every 3 seconds
    setInterval(fetchLogs, 3000);
});
