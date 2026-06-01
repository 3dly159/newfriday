// Browser face recognition with graceful profile fallback.
// Loads face-api.js from CDN; any failure (no lib, no camera, no permission,
// not enrolled, no match) resolves to mode 'profile'.
const FACEAPI = 'https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js';
const MODELS = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.13/model/';
const KEY = 'friday_face_descriptor';

function pickGreetingMode(hasCamera, enrolled, matched) {
    return (hasCamera && enrolled && matched) ? 'face' : 'profile';
}

async function _loadLib() {
    if (window.faceapi) return true;
    await new Promise((res, rej) => {
        const s = document.createElement('script');
        s.src = FACEAPI; s.onload = res; s.onerror = rej;
        document.head.appendChild(s);
    });
    return !!window.faceapi;
}

async function _camera() {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    const video = document.createElement('video');
    video.srcObject = stream; video.muted = true; await video.play();
    return { video, stream };
}

async function recognize() {
    // Returns 'face' or 'profile'. Never throws.
    try {
        if (!await _loadLib()) return 'profile';
        await faceapi.nets.tinyFaceDetector.loadFromUri(MODELS);
        await faceapi.nets.faceRecognitionNet.loadFromUri(MODELS);
        await faceapi.nets.faceLandmark68Net.loadFromUri(MODELS);
        const enrolled = localStorage.getItem(KEY);
        const { video, stream } = await _camera();
        const det = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions())
            .withFaceLandmarks().withFaceDescriptor();
        let matched = false;
        if (det && enrolled) {
            const saved = new Float32Array(JSON.parse(enrolled));
            const dist = faceapi.euclideanDistance(saved, det.descriptor);
            matched = dist < 0.55;
        } else if (det && !enrolled) {
            // First run: enroll this face for next time.
            localStorage.setItem(KEY, JSON.stringify(Array.from(det.descriptor)));
        }
        stream.getTracks().forEach(t => t.stop());
        return pickGreetingMode(true, !!enrolled, matched);
    } catch (e) {
        console.log('[recognition] falling back to profile:', e.message);
        return 'profile';
    }
}

async function _reportPresence(present) {
    try {
        await fetch('/api/presence', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ present }),
        });
    } catch (e) { /* best-effort */ }
}

// Continuously report whether the ENROLLED user is in front of the camera, so
// backend proactivity only speaks when you're present. Holds one camera stream
// open and polls every `intervalMs`. If anything fails (no camera/permission/
// enrollment), it simply never reports 'present' → backend stays silent (strict).
async function startPresenceMonitor(intervalMs = 5000) {
    try {
        if (!await _loadLib()) return;
        await faceapi.nets.tinyFaceDetector.loadFromUri(MODELS);
        await faceapi.nets.faceRecognitionNet.loadFromUri(MODELS);
        await faceapi.nets.faceLandmark68Net.loadFromUri(MODELS);
        const enrolled = localStorage.getItem(KEY);
        if (!enrolled) return; // can't match "you" without enrollment → stay silent
        const saved = new Float32Array(JSON.parse(enrolled));
        const { video } = await _camera(); // keep stream open for the session

        const tick = async () => {
            let present = false;
            try {
                const det = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions())
                    .withFaceLandmarks().withFaceDescriptor();
                if (det) {
                    present = faceapi.euclideanDistance(saved, det.descriptor) < 0.55;
                }
            } catch (e) { present = false; }
            await _reportPresence(present);
        };
        await tick();
        setInterval(tick, intervalMs);
    } catch (e) {
        console.log('[recognition] presence monitor unavailable:', e.message);
        // No reports → backend treats user as absent (strict). Intentional.
    }
}

window.Recognition = { recognize, pickGreetingMode, startPresenceMonitor };
