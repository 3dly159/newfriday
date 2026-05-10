let socket;
let mediaRecorder;
let audioChunks = [];

function connectWebSocket() {
    socket = new WebSocket(`ws://${window.location.host}/ws/voice`);
    socket.binaryType = 'arraybuffer';

    socket.onmessage = async (event) => {
        if (typeof event.data === 'string') {
            const msg = JSON.parse(event.data);
            console.log('Friday:', msg.text);
        } else {
            // Audio response
            playResponse(event.data);
        }
    };

    socket.onclose = () => {
        setTimeout(connectWebSocket, 1000);
    };
}

async function playResponse(buffer) {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createBufferSource();
    const analyser = audioContext.createAnalyser();

    const audioBuffer = await audioContext.decodeAudioData(buffer);
    source.buffer = audioBuffer;

    source.connect(analyser);
    analyser.connect(audioContext.destination);

    analyser.fftSize = 256;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    source.start(0);

    function updateOrb() {
        if (source.onended) return;
        analyser.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        const normalized = average / 128;
        if (window.setVoiceBright) {
            window.setVoiceBright(normalized);
        }
        if (audioContext.state !== 'closed' && source.playbackState !== 3) {
            requestAnimationFrame(updateOrb);
        }
    }

    updateOrb();
    source.onended = () => {
        if (window.setVoiceBright) window.setVoiceBright(0);
    };
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

// Initialize
connectWebSocket();
// startRecording(); // User gesture required for production, calling from console for dev
