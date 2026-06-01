let socket, mediaRecorder, micStream;
let audioCtx, micAnalyser, bargeFrames = 0;
const BARGE_RMS = 0.08;

let audioQueue = [];
let isPlaying = false;
let pendingCaption = null;

function setState(state) {
    document.body.dataset.state = state;
    window.Orb?.setState(state);
    window.Hud?.setStateLabel(state);
}

function connect() {
    socket = new WebSocket(`ws://${location.host}/ws/voice`);
    socket.binaryType = 'arraybuffer';
    socket.onmessage = async (e) => {
        if (typeof e.data === 'string') return handleEvent(JSON.parse(e.data));
        if (pendingCaption && e.data) {
            audioQueue.push({ buffer: e.data, ...pendingCaption });
            pendingCaption = null;
            if (!isPlaying) pump();
        }
    };
    socket.onclose = () => setTimeout(connect, 1000);
}

function handleEvent(msg) {
    switch (msg.type) {
        case 'state':
            setState(msg.state);
            if (msg.state !== 'idle') {
                window.Conversation?.open();
            } else {
                window.Conversation?.scheduleRecede();
                window.Orb?.resetColor();   // back to arc-reactor blue when done
            }
            break;
        case 'mood': window.Orb?.setColor(msg.orb_color); break;
        case 'transcript': window.Conversation?.addMessage(msg.role, msg.text); break;
        case 'caption':
            pendingCaption = { segment_id: msg.segment_id, words: msg.words, mode: msg.mode, text: msg.text };
            break;
        case 'action': window.Hud?.action(msg); break;
        case 'arg_unlocked': window.Hud?.glitch(); break;
        case 'status': break;
    }
}

async function pump() {
    if (!audioQueue.length) { isPlaying = false; if (document.body.dataset.state === 'speaking') setState('idle'); return; }
    isPlaying = true;
    const seg = audioQueue.shift();
    try { await playSegment(seg); } catch (err) { console.error('playback', err); }
    pump();
}

async function playSegment(seg) {
    if (!seg || !seg.buffer) return;
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    // Browsers suspend the AudioContext until a user gesture; resume so the
    // first reply after a click/keypress actually plays.
    if (audioCtx.state === 'suspended') { try { await audioCtx.resume(); } catch (e) {} }
    const buf = await audioCtx.decodeAudioData(seg.buffer.slice(0));
    const src = audioCtx.createBufferSource();
    const analyser = audioCtx.createAnalyser();
    src.buffer = buf; src.connect(analyser); analyser.connect(audioCtx.destination);
    analyser.fftSize = 256;
    const data = new Uint8Array(analyser.frequencyBinCount);
    window.Captions?.play(seg, buf.duration * 1000);

    return new Promise((resolve) => {
        src.onended = () => { window.Orb?.setVoiceBright(0); resolve(); };
        src.start(0);
        (function tick() {
            if (!isPlaying) return;
            analyser.getByteFrequencyData(data);
            const avg = data.reduce((a, b) => a + b, 0) / data.length;
            window.Orb?.setVoiceBright(avg / 128);
            requestAnimationFrame(tick);
        })();
    });
}

function stopSpeaking() {
    audioQueue = []; pendingCaption = null; isPlaying = false;
    window.Captions?.clear();
    setState('idle');
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'interrupt' }));
}

async function startRecording() {
    micStream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
    startMicVAD(micStream);
    const opts = { mimeType: 'audio/webm;codecs=opus' };
    if (!MediaRecorder.isTypeSupported(opts.mimeType)) delete opts.mimeType;
    mediaRecorder = new MediaRecorder(micStream, opts);
    mediaRecorder.ondataavailable = (ev) => {
        if (ev.data.size > 0 && socket?.readyState === WebSocket.OPEN) socket.send(ev.data);
    };
    const iv = setInterval(() => {
        if (mediaRecorder.state === 'recording') { mediaRecorder.stop(); mediaRecorder.start(); }
        else clearInterval(iv);
    }, 3000);
    mediaRecorder.start();
    setState('listening');
}
function stopRecording() {
    micAnalyser = null;
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop(); mediaRecorder.stream.getTracks().forEach(t => t.stop());
    }
    setState('idle');
}
function startMicVAD(stream) {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const src = ctx.createMediaStreamSource(stream);
    micAnalyser = ctx.createAnalyser(); micAnalyser.fftSize = 512; src.connect(micAnalyser);
    const buf = new Uint8Array(micAnalyser.fftSize);
    (function tick() {
        if (!micAnalyser) return;
        micAnalyser.getByteTimeDomainData(buf);
        let s = 0; for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; s += v * v; }
        const rms = Math.sqrt(s / buf.length);
        if (isPlaying && rms > BARGE_RMS) { if (++bargeFrames >= 3) { stopSpeaking(); bargeFrames = 0; } }
        else bargeFrames = 0;
        requestAnimationFrame(tick);
    })();
}

function sendText() {
    const input = document.getElementById('text-input');
    const content = input.value.trim();
    if (!content || socket?.readyState !== WebSocket.OPEN) return;
    window.Conversation?.open();
    socket.send(JSON.stringify({ type: 'text', content }));
    input.value = '';
}

let listening = false;
function toggleMic() {
    listening = !listening;
    document.getElementById('mic-trigger').classList.toggle('active', listening);
    listening ? startRecording() : stopRecording();
}
window.addEventListener('DOMContentLoaded', () => {
    document.getElementById('mic-trigger').addEventListener('click', toggleMic);
    document.getElementById('send-btn').addEventListener('click', sendText);
    document.getElementById('text-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') sendText(); });
    window.Hud?.init();
    connect();
});
