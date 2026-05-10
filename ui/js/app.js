let socket;
let mediaRecorder;
let audioQueue = [];
let isPlaying = false;
let currentAudioContext = null;
let currentHeldText = "";

function connectWebSocket() {
    socket = new WebSocket(`ws://${window.location.host}/ws/voice`);
    socket.binaryType = 'arraybuffer';

    socket.onmessage = async (event) => {
        if (typeof event.data === 'string') {
            const msg = JSON.parse(event.data);
            if (msg.type === 'speak_segment') {
                currentHeldText = msg.text;
                if (currentHeldText.includes("PENDING_APPROVAL:")) {
                    handleApprovalRequest(currentHeldText);
                }
                if (msg.orb_color && window.setOrbColor) {
                    window.setOrbColor(msg.orb_color);
                }
            } else if (msg.type === 'status') {
                setStatus(msg.state);
            } else if (msg.type === 'arg_unlocked') {
                triggerGlitch();
            }
        } else {
            // Audio response segment
            audioQueue.push({ buffer: event.data, text: currentHeldText });
            if (!isPlaying) pumpQueue();
        }
    };

    socket.onclose = () => {
        setTimeout(connectWebSocket, 1000);
    };
}

async function pumpQueue() {
    if (audioQueue.length === 0) {
        isPlaying = false;
        setStatus('idle');
        return;
    }

    isPlaying = true;
    const segment = audioQueue.shift();
    console.log('Friday:', segment.text);

    try {
        await playSegment(segment.buffer);
    } catch (e) {
        console.error('Playback error:', e);
    }

    pumpQueue();
}

async function playSegment(buffer) {
    if (!currentAudioContext) {
        currentAudioContext = new (window.AudioContext || window.webkitAudioContext)();
    }

    const audioBuffer = await currentAudioContext.decodeAudioData(buffer);
    const source = currentAudioContext.createBufferSource();
    const analyser = currentAudioContext.createAnalyser();

    source.buffer = audioBuffer;
    source.connect(analyser);
    analyser.connect(currentAudioContext.destination);

    analyser.fftSize = 256;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    return new Promise((resolve) => {
        source.onended = () => {
            if (window.setVoiceBright) window.setVoiceBright(0);
            resolve();
        };

        source.start(0);

        function updateOrb() {
            if (!isPlaying) return;
            analyser.getByteFrequencyData(dataArray);
            const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
            const normalized = average / 128;
            if (window.setVoiceBright) {
                window.setVoiceBright(normalized);
            }
            requestAnimationFrame(updateOrb);
        }
        updateOrb();
    });
}

async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
            socket.send(event.data);
        }
    };

    // Send audio every 3 seconds for now (Phase 1 simplicity)
    mediaRecorder.start(3000);
}

// UI Elements
const micTrigger = document.getElementById('mic-trigger');
const statusDot = document.getElementById('status-dot');
const panelToggle = document.getElementById('panel-toggle');
const activityPanel = document.getElementById('activity-panel');

// State
let isListening = false;

// Event Listeners
micTrigger.addEventListener('click', toggleListening);
panelToggle.addEventListener('click', () => {
    activityPanel.classList.toggle('collapsed');
    panelToggle.innerText = activityPanel.classList.contains('collapsed') ? '◀' : '▶';
});

function toggleListening() {
    isListening = !isListening;
    micTrigger.classList.toggle('active', isListening);
    statusDot.className = 'status-dot ' + (isListening ? 'listening' : '');

    if (isListening) {
        startRecording();
    } else {
        stopRecording();
    }

    // Dispatch custom event
    window.dispatchEvent(new CustomEvent('friday:mic-toggle', { detail: { active: isListening } }));
}

function setStatus(state) {
    // state: 'idle', 'listening', 'processing'
    statusDot.className = 'status-dot ' + (state !== 'idle' ? state : '');
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
}

function triggerGlitch() {
    document.body.classList.add('glitch-mode');
    setTimeout(() => {
        document.body.classList.remove('glitch-mode');
    }, 3000);
}
window.triggerGlitch = triggerGlitch;

function handleApprovalRequest(text) {
    let perm;
    if (typeof text === 'string') {
        perm = text.split(": ")[1];
    } else if (text && text.category) {
        perm = text.category;
    } else {
        perm = "Unknown";
    }
    const toast = document.getElementById('permission-toast');
    const msg = document.getElementById('toast-message');
    msg.innerText = `Friday is requesting permission: ${perm.toUpperCase()}`;
    toast.classList.remove('hidden');

    document.getElementById('toast-allow').onclick = async () => {
        const perms = {};
        perms[perm] = 'allow';
        await fetch('/api/permissions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(perms)
        });
        toast.classList.add('hidden');
    };

    document.getElementById('toast-deny').onclick = async () => {
        const perms = {};
        perms[perm] = 'deny';
        await fetch('/api/permissions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(perms)
        });
        toast.classList.add('hidden');
    };
}
window.handleApprovalRequest = handleApprovalRequest;

// Settings Management
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const settingsForm = document.getElementById('settings-form');
const saveSettingsBtn = document.getElementById('save-settings');
const closeSettingsBtn = document.getElementById('close-settings');

settingsBtn.addEventListener('click', async () => {
    const resp = await fetch('/api/config');
    const config = await resp.json();
    renderSettings(config);

    const permsResp = await fetch('/api/permissions');
    const perms = await permsResp.json();
    renderPermissions(perms);

    settingsModal.classList.remove('hidden');
});

closeSettingsBtn.addEventListener('click', () => {
    settingsModal.classList.add('hidden');
});

saveSettingsBtn.addEventListener('click', async () => {
    const config = collectSettings();
    await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    });

    const perms = collectPermissions();
    await fetch('/api/permissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(perms)
    });

    settingsModal.classList.add('hidden');
});

function renderPermissions(perms) {
    const container = document.getElementById('permissions-form');
    container.innerHTML = '';
    if (typeof perms !== 'object' || Array.isArray(perms)) return;
    for (const key in perms) {
        const label = document.createElement('label');
        label.innerText = key.replace(/_/g, ' ').toUpperCase();

        const select = document.createElement('select');
        select.dataset.key = key;
        ['allow', 'ask', 'deny'].forEach(opt => {
            const o = document.createElement('option');
            o.value = opt;
            o.text = opt.toUpperCase();
            if (opt === perms[key]) o.selected = true;
            select.appendChild(o);
        });
        select.style.background = 'rgba(255,255,255,0.1)';
        select.style.border = '1px solid rgba(255,255,255,0.2)';
        select.style.color = 'white';

        container.appendChild(label);
        container.appendChild(select);
    }
}

function collectPermissions() {
    const perms = {};
    const selects = document.getElementById('permissions-form').querySelectorAll('select');
    selects.forEach(s => {
        perms[s.dataset.key] = s.value;
    });
    return perms;
}

function renderSettings(config) {
    settingsForm.innerHTML = '';
    if (typeof config !== 'object' || Array.isArray(config)) return;
    for (const section in config) {
        const header = document.createElement('h3');
        header.innerText = section.toUpperCase();
        header.style.gridColumn = '1 / -1';
        header.style.marginTop = '10px';
        header.style.fontSize = '12px';
        settingsForm.appendChild(header);

        for (const key in config[section]) {
            const label = document.createElement('label');
            label.innerText = key;
            const input = document.createElement('input');
            input.type = 'text';
            input.value = config[section][key];
            input.dataset.section = section;
            input.dataset.key = key;
            input.style.background = 'rgba(255,255,255,0.1)';
            input.style.border = '1px solid rgba(255,255,255,0.2)';
            input.style.color = 'white';
            input.style.padding = '5px';

            settingsForm.appendChild(label);
            settingsForm.appendChild(input);
        }
    }
}

function collectSettings() {
    const config = {};
    const inputs = settingsForm.querySelectorAll('input');
    inputs.forEach(input => {
        const { section, key } = input.dataset;
        if (!config[section]) config[section] = {};
        let val = input.value;
        if (!isNaN(val) && val.trim() !== '') val = parseFloat(val);
        config[section][key] = val;
    });
    return config;
}

// Vitals Monitoring
async function updateVitals() {
    try {
        const vitalsResp = await fetch('/api/vitals');
        const vitals = await vitalsResp.json();

        document.getElementById('cpu-bar').style.width = vitals.cpu_usage + '%';
        document.getElementById('ram-bar').style.width = vitals.memory_usage + '%';

        // Also update tasks while we're at it
        const configResp = await fetch('/api/config');
        const config = await configResp.json();
        renderTaskList(config.system_memory?.task || []);
    } catch (e) {
        // Silently fail if endpoint not yet ready
    }
}

function renderTaskList(tasks) {
    const list = document.getElementById('task-list');
    const count = document.getElementById('task-count');
    if (!list) return;

    list.innerHTML = '';
    count.innerText = tasks.length;

    tasks.forEach(task => {
        const div = document.createElement('div');
        div.className = `task-item entry ${task.status}`;
        div.innerHTML = `
            <div class="priority ${task.priority}">${task.priority}</div>
            <div class="name">${task.name}</div>
            <div class="desc">${task.desc}</div>
        `;
        list.appendChild(div);
    });
}

setInterval(updateVitals, 2000);

import NeuralMap from './neural.js';
const neuralMap = new NeuralMap('neural-map-container');

document.getElementById('neural-map-btn').addEventListener('click', () => {
    const container = document.getElementById('neural-map-container');
    if (container.style.display === 'none') {
        container.style.display = 'block';
    } else {
        container.style.display = 'none';
    }
});

// Initialize
connectWebSocket();
